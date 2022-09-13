import logging
import os
import signal
from datetime import timedelta
from subprocess import Popen
from typing import Callable, Dict, Optional
from ops.charm import CharmBase, Object, CharmEvents
from ops.framework import StoredState, EventSource, EventBase

logger = logging.getLogger('resurrect')

juju_dispatch_path = 'JUJU_DISPATCH_PATH'
operator_dispatch = 'OPERATOR_DISPATCH'


class NotStarted(RuntimeError):
    """Raised when attempting to stop a non-started resurrect."""


class AlreadyPrimed(RuntimeError):
    """Raised when attempting to prime Resurrect twice."""


class ResurrectEvent(EventBase):
    pass


class ResurrectEvents(CharmEvents):
    timeout = EventSource(ResurrectEvent)


class Resurrect(Object):
    on = ResurrectEvents()
    _stored = StoredState()

    def __init__(self, parent: CharmBase,
                 key='resurrect',
                 oneshot: Optional[timedelta] = None,
                 every: Optional[timedelta] = None,
                 allow_empty_env: bool = False):
        super().__init__(parent, key)
        if not (oneshot or every) or (oneshot and every):
            raise ValueError('provide exactly one of `oneshot` and `every`.')

        self._charm = parent
        self._every = every
        self._oneshot = oneshot
        self._allow_empty_env = allow_empty_env

        self._stored.set_default(env={}, pid=None)

    def is_started(self):
        return self._stored.pid

    def prime(self, override: Dict[str, str] = None, overwrite: bool = False,
              use_os_env=True):
        """Store the current environment for later usage.

        If you pass use_os_env, the basis env will be provided by os.environ;
        otherwise it will be empty.
        Any override you pass will update that basis.
        """
        if pid := self.is_started():
            if self._every:
                # probably unintentional
                logger.warning(f"re-priming an already running command (pid={pid})!")
            else:
                # possibly unintentional?
                logger.debug(f"re-priming an already launched one-shot command (pid={pid});"
                             f"this will only have effect if you restart it.")

        if self._stored.env and not overwrite:
            logger.warning(f"{self} is already primed. Overriding...")

        new_env = dict(os.environ) if use_os_env else {}
        new_env.update(override)
        self._stored.env = new_env

    def start(self, env: Dict[str, str] = None) -> int:
        """Launch the process.

        Returns the pid of the launched process.
        """
        if self.is_started() and self._every:
            logger.warning(f"this Resurrect is already running! {self._stored.pid}")

        if env is None:
            logger.debug('using stored env')
            env = self._stored.env

        if not env and not self._allow_empty_env:
            logger.warning('launching resurrect process with empty env. If this '
                           'is calling `dispatch`, there will most definitely be errors.')

        logger.info(f"overriding {env.get(juju_dispatch_path)} with hooks/resurrect")
        env[juju_dispatch_path] = 'hooks/resurrect'

        # we need to set this key in order to tell the agent
        # that the charm is executing itself; otherwise it will look for
        # an event registered **on the charm**!.
        env[f'{operator_dispatch}'] = '1'

        execute_charm = f"{os.getenv('JUJU_CHARM_DIR')}/dispatch"

        if self._every:
            resurrect_command = f"watch -n {self._every.seconds} {execute_charm!r}".split()
        elif self._oneshot:
            # if oneshot, we're running in shell mode, and we don't need to split the args.
            resurrect_command = f"sleep {self._oneshot.seconds}; {execute_charm}"
        else:
            raise RuntimeError('Either _every or _oneshot need to be set.')

        proc = Popen(resurrect_command, env=env, shell=bool(self._oneshot))

        logger.info(f"Resurrect process running on pid={proc.pid}")
        self._stored.pid = proc.pid
        return proc.pid

    def stop(self, pid=None, sig=signal.SIGKILL):
        """Kill the running resurrect process."""
        pid = pid if pid is not None else self._stored.pid
        if pid is None:
            raise NotStarted()
        os.kill(pid, sig)
        self._stored.pid = None
