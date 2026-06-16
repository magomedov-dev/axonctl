"""UI tree layer (pure, no I/O).

Value types for geometry (:class:`Bounds`, :class:`Point`), the parsed UI tree
(:class:`UiNode` / :class:`UiTree`), the window model (:class:`Window` /
:class:`WindowList`), and the :class:`Selector`. Everything here operates on a
dump that already arrived — embodying the stateless-device principle: search,
navigation, partial matching and regex all run on the PC. These types are part of
the public API and re-exported from :mod:`axonctl`.
"""

from __future__ import annotations
