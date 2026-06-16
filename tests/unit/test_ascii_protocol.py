"""Guard: protocol keys and identifiers in src must be ASCII-only.

Cyrillic homoglyphs (с/а/е/о, ...) are visually identical to Latin letters. One
slipping into a protocol key (``resourceId``, ``windowId``, ``nodeAction``) or an
identifier would break the wire format or the code while looking perfectly
correct. Docstrings/comments may contain non-ASCII text and are exempt.
"""

from __future__ import annotations

import ast
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "axonctl"


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def test_protocol_strings_and_identifiers_are_ascii() -> None:
    offenders: list[str] = []
    # inspect.py is a presentation-only HTML/CSS/JS template (typographic chars
    # like … “ ” · are intentional); it carries no protocol keys.
    exempt = {"inspect.py"}
    for path in sorted(_SRC.rglob("*.py")):
        if path.name in exempt:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_constant_ids(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and not node.value.isascii()
            ):
                offenders.append(f"{path}:{node.lineno} string {node.value!r}")
            if isinstance(node, ast.Name) and not node.id.isascii():
                offenders.append(f"{path}:{node.lineno} name {node.id!r}")
    assert not offenders, "non-ASCII in protocol-critical code:\n" + "\n".join(
        offenders
    )
