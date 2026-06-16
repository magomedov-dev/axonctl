# Selectors


A [`Selector`][axonctl.Selector] describes *which* node(s) to find in a dumped UI
tree. All matching runs on the PC over a dump (the stateless-device principle), so
you get rich matching — exact, substring, regex, positional, and containment —
without any device round-trips beyond the dump itself.

## Factories

Prefer the factories over the raw constructor:

```python
from axonctl import Selector

Selector.id("com.app:id/login")        # by resourceId
Selector.text("Sign in")               # by visible text
Selector.text_contains("Signing")      # substring of text
Selector.desc("Profile photo")         # by contentDesc
Selector.cls("android.widget.EditText")  # by Android class
```

The raw form is `Selector(by=..., value=..., match=..., index=...)`, where `by` is
`resourceId` / `text` / `class` / `contentDesc` (mirroring the protocol's `by`).

## Match modes

`match` controls how `value` is compared:

| mode | meaning |
|------|---------|
| `exact` (default) | full-string equality |
| `contains` | substring |
| `regex` | matches **anywhere** (like the agent's Kotlin regex); anchor with `^` / `$` |

```python
Selector.text("OK")                          # exact
Selector.text("Sign", match="contains")      # substring (same as text_contains)
Selector.text(r"^Item \d+$", match="regex")  # anchored full match
Selector.id(r"com\.app:id/row_\d+", match="regex")
```

## Index — picking the N-th match

When several nodes match, `index` selects one (0-based):

```python
first_field = Selector.cls("android.widget.EditText", index=0)
second_field = Selector.cls("android.widget.EditText", index=1)
```

`find` returns the indexed match (or the first when `index` is unset);
`find_all` returns all matches (or a single-element list when `index` is set).

## `.within(...)` — find X inside Y

Scope a search to the descendants of another match:

```python
ok_in_dialog = Selector.text("OK").within(Selector.id("com.app:id/confirm_dialog"))
row_title = Selector.id("com.app:id/title").within(Selector.cls("...RecyclerView"))
```

`.within(...)` is evaluated on the PC for **queries** (`find`, `find_all`,
`wait_for`, `wait_gone`).

!!! warning "`.within(...)` and node actions"
    Node **actions** (`click`, `set_text`, ...) send the selector to the agent,
    which matches by bare criteria and **cannot** express containment. Passing a
    `.within(...)` selector to an action raises
    [`UnsupportedSelector`][axonctl.UnsupportedSelector] (never a silent
    wrong-target action). To act inside a region, use `window_id` for a window/
    dialog, a more specific selector, or `tap(node.center)` after a `find`.

## Where selectors are evaluated

- **Queries** (`Device.find`, `Device.find_all`, `UiTree.find`, `Device.wait_*`)
  evaluate the whole selector — including `match`, `index`, and `.within(...)` —
  on the PC.
- **Actions** (`Device.click`, `set_text`, `scroll`, ...) send `by` / `value` /
  `match` / `index` (and optional `window_id`) to the agent, which re-finds from a
  fresh root and acts. `.within(...)` is not supported here.

See also: [The UI tree](tree.md) and [Waiting](waiting.md).
