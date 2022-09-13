Simple charm resurrection library.

Usage:

```python
class MyCharm(CharmBase):
    def __init__(...):
        self.resurrect = Resurrect(self, every=timedelta(hours=5))
        self.framework.observe(self.resurrect.on.timeout, self._on_resurrect_timeout)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.remove, self._on_remove)
        
    def _on_start(self, _):
        # prime the Resurrect with the current env, plus this additional custom var.
        self.resurrect.prime({'CUSTOM_ENV_VAR':'foo'})
        self.resurrect.start()
        
    def _on_resurrect_timeout(self, _):
        print("I'm 5 hours old!")
        _do_scheduled_task()
        # this will be called with the env you stored with prime()
        assert os.getenv('CUSTOM_ENV_VAR') == 'foo'
        
    def _on_remove(self, _):
        self.resurrect.stop()
```
