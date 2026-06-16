"""Fleet layer.

Everything above a single device: the adb device watcher, port allocator, adb
bridge, tag-based groups, the :class:`FleetController` (lifecycle, registry,
attach/detach) and the executor that runs user scenarios across device groups.
Only :class:`FleetController` is public (re-exported from :mod:`axonctl`); the
rest is internal.
"""

from __future__ import annotations
