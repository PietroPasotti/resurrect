#!/usr/bin/env bash
LIB_V=${LIB_VERSION:-v0}
charmcraft publish-lib "charms.resurrect.$LIB_V.resurrect"  # $ TEMPLATE: Filled in by ./scripts/init.sh
