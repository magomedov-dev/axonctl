# The UI tree


A dump is a snapshot of one window's accessibility tree. You search and navigate
it entirely on the PC.

## Dumping

```python
tree = await device.dump()                       # active window, compressed
tree = await device.dump(compress=False)         # include center + empty children
tree = await device.dump(max_depth=3)            # bound the depth
tree = await device.dump(window_id=12)           # a specific window
```

[`UiTree`][axonctl.UiTree] has `root`, `screen` (the generation counter), and
`package` (the foreground app).

!!! tip "Dump once, query many"
    `Device.find`/`find_all` dump then search in one call — convenient, but each
    call is a fresh dump. For several queries on the same screen, `dump()` once and
    reuse the tree.

## Searching

```python
from axonctl import Selector

node = tree.find(Selector.id("com.app:id/title"))        # UiNode | None
buttons = tree.find_all(Selector.cls("android.widget.Button"))  # list[UiNode]
```

Or in one call against a fresh dump:

```python
node = await device.find(Selector.text("Continue"))
nodes = await device.find_all(Selector.cls("android.widget.EditText"))
```

## Nodes

[`UiNode`][axonctl.UiNode] mirrors the protocol's node schema (snake_case):
`node_id`, `parent_id`, `class_name`, `text`, `resource_id`, `content_desc`,
`clickable`, `enabled`, `focused`, `bounds`, `center`, `children`.

```python
node.text, node.resource_id, node.class_name
node.bounds.width, node.bounds.height, node.bounds.center
node.center          # Point(x, y) — handy for tap(node.center.x, node.center.y)
```

!!! warning "A node is a snapshot, not a handle"
    `node_id` is valid only within its dump and never travels back to the device.
    To act on a found node, use criteria (`click(Selector...)`) or
    `tap(node.center)` — you cannot "click this node object".

## Navigation

Downward navigation needs no setup:

```python
for child in node.children: ...
for desc in node.descendants(): ...   # pre-order
for n in node.walk(): ...             # node + descendants
```

Upward navigation (`parent`, `ancestors`) needs parent links, which the tree
builds **lazily** — only when you search via `tree.find`/`find_all` or call
`tree.link()` explicitly. A dump you only serialize never pays for linking.

```python
node = tree.find(Selector.id("com.app:id/user"))   # this links the tree
node.parent                                          # UiNode | None
list(node.ancestors())                               # parent → ... → root
```

## Counting / inspecting

```python
count = sum(1 for _ in tree.root.walk())
texts = [n.text for n in tree.root.walk() if n.text]
```

The `examples/inspect_ui.py` script prints a compact tree — handy for discovering
selectors.

See also: [Selectors](selectors.md) and [Windows & dialogs](windows.md).
