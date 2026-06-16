"""Element selectors.

A :class:`Selector` describes *which* node(s) to find in a dumped UI tree. All
matching happens on the PC over a dump (the stateless-device principle): exact,
substring, and regex matching; an optional positional ``index``; and an optional
``within`` constraint ("find X inside Y"). The same ``by``/``value``/``match``
fields map directly onto the agent's ``nodeAction`` parameters in a later stage.

Example:
    ```python
    from axonctl import Selector

    Selector.id("com.app:id/login")
    Selector.text("Sign in")
    Selector.text_contains("Signing")
    Selector.cls("android.widget.EditText", index=0)
    Selector.text("OK").within(Selector.id("com.app:id/dialog"))
    ```
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .node import UiNode

#: Which node attribute to match against (mirrors the protocol's ``by``).
SelectorBy = Literal["resourceId", "text", "class", "contentDesc"]
#: How to compare ``value`` against the attribute.
MatchMode = Literal["exact", "contains", "regex"]

_VALID_BY: frozenset[str] = frozenset({"resourceId", "text", "class", "contentDesc"})
_VALID_MATCH: frozenset[str] = frozenset({"exact", "contains", "regex"})


@functools.lru_cache(maxsize=512)
def _compiled(pattern: str) -> re.Pattern[str]:
    """Compile and cache a regex (matches anywhere, like the agent's Kotlin regex)."""
    return re.compile(pattern)


@dataclass(frozen=True, slots=True)
class Selector:
    """A declarative description of nodes to find in a UI tree.

    Attributes:
        by: Which attribute to match (``resourceId``/``text``/``class``/
            ``contentDesc``).
        value: The value to compare against.
        match: Comparison mode: ``exact`` (default), ``contains``, or ``regex``
            (matches anywhere; anchor with ``^``/``$`` for a full match).
        index: When set, select the N-th match (0-based) instead of the first.
        container: When set, restrict matches to descendants of nodes matching
            this selector (set via :meth:`within`).
    """

    by: SelectorBy
    value: str
    match: MatchMode = "exact"
    index: int | None = None
    container: Selector | None = None

    def __post_init__(self) -> None:
        if self.by not in _VALID_BY:
            raise ValueError(f"invalid selector 'by': {self.by!r}")
        if self.match not in _VALID_MATCH:
            raise ValueError(f"invalid selector 'match': {self.match!r}")

    # -- Factories ---------------------------------------------------------

    @classmethod
    def id(
        cls, value: str, *, match: MatchMode = "exact", index: int | None = None
    ) -> Selector:
        """Select by ``resourceId``."""
        return cls(by="resourceId", value=value, match=match, index=index)

    @classmethod
    def text(
        cls, value: str, *, match: MatchMode = "exact", index: int | None = None
    ) -> Selector:
        """Select by visible ``text``."""
        return cls(by="text", value=value, match=match, index=index)

    @classmethod
    def text_contains(cls, value: str, *, index: int | None = None) -> Selector:
        """Select nodes whose ``text`` contains ``value``."""
        return cls(by="text", value=value, match="contains", index=index)

    @classmethod
    def desc(
        cls, value: str, *, match: MatchMode = "exact", index: int | None = None
    ) -> Selector:
        """Select by ``contentDesc``."""
        return cls(by="contentDesc", value=value, match=match, index=index)

    @classmethod
    def cls(  # noqa: A003 - "cls" reads naturally for a class-name selector
        klass, value: str, *, match: MatchMode = "exact", index: int | None = None
    ) -> Selector:
        """Select by Android view ``class`` name."""
        return klass(by="class", value=value, match=match, index=index)

    # -- Composition -------------------------------------------------------

    def within(self, container: Selector) -> Selector:
        """Return a copy constrained to descendants of ``container`` matches.

        Args:
            container: Selector identifying the enclosing node(s).

        Returns:
            A new selector that only matches inside ``container``.
        """
        return replace(self, container=container)

    # -- Matching ----------------------------------------------------------

    def matches(self, node: UiNode) -> bool:
        """Return whether ``node`` satisfies the by/value/match criteria.

        Ignores ``index`` and ``container`` (which constrain the search space,
        not a single node).

        Args:
            node: The node to test.

        Returns:
            ``True`` if the node's attribute matches.
        """
        actual = self._attribute(node)
        if actual is None:
            return False
        if self.match == "exact":
            return actual == self.value
        if self.match == "contains":
            return self.value in actual
        return _compiled(self.value).search(actual) is not None

    def find(self, root: UiNode) -> UiNode | None:
        """Return the selected node in ``root``'s subtree, or ``None``.

        Args:
            root: Node whose subtree (including itself) is searched.

        Returns:
            The match at ``index`` if set, else the first match, else ``None``.
        """
        matches = self._all_matches(root)
        if self.index is not None:
            return matches[self.index] if 0 <= self.index < len(matches) else None
        return matches[0] if matches else None

    def find_all(self, root: UiNode) -> list[UiNode]:
        """Return all selected nodes in ``root``'s subtree, in pre-order.

        Args:
            root: Node whose subtree (including itself) is searched.

        Returns:
            Every match; a single-element (or empty) list when ``index`` is set.
        """
        matches = self._all_matches(root)
        if self.index is not None:
            return matches[self.index : self.index + 1]
        return matches

    # -- Internals ---------------------------------------------------------

    def _attribute(self, node: UiNode) -> str | None:
        if self.by == "resourceId":
            return node.resource_id
        if self.by == "text":
            return node.text
        if self.by == "class":
            return node.class_name
        return node.content_desc

    def _all_matches(self, root: UiNode) -> list[UiNode]:
        return [node for node in self._scope(root) if self.matches(node)]

    def _scope(self, root: UiNode) -> Iterator[UiNode]:
        if self.container is None:
            yield from root.walk()
            return
        seen: set[int] = set()
        for container in self.container.find_all(root):
            for node in container.descendants():
                key = id(node)
                if key not in seen:
                    seen.add(key)
                    yield node
