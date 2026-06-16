# Дерево UI


Дамп — это снимок дерева доступности одного окна. Поиск и навигацию по нему ты
выполняешь целиком на ПК.

## Снятие дампа

```python
tree = await device.dump()                       # active window, compressed
tree = await device.dump(compress=False)         # include center + empty children
tree = await device.dump(max_depth=3)            # bound the depth
tree = await device.dump(window_id=12)           # a specific window
```

У [`UiTree`][axonctl.UiTree] есть `root`, `screen` (счётчик поколений) и
`package` (приложение на переднем плане).

!!! tip "Дамп один раз, запросов много"
    `Device.find`/`find_all` снимают дамп и ищут за один вызов — удобно, но каждый
    вызов делает свежий дамп. Для нескольких запросов по одному экрану сними
    `dump()` один раз и переиспользуй дерево.

## Поиск

```python
from axonctl import Selector

node = tree.find(Selector.id("com.app:id/title"))        # UiNode | None
buttons = tree.find_all(Selector.cls("android.widget.Button"))  # list[UiNode]
```

Или одним вызовом по свежему дампу:

```python
node = await device.find(Selector.text("Continue"))
nodes = await device.find_all(Selector.cls("android.widget.EditText"))
```

## Узлы

[`UiNode`][axonctl.UiNode] зеркалит схему узла из протокола (snake_case):
`node_id`, `parent_id`, `class_name`, `text`, `resource_id`, `content_desc`,
`clickable`, `enabled`, `focused`, `bounds`, `center`, `children`.

```python
node.text, node.resource_id, node.class_name
node.bounds.width, node.bounds.height, node.bounds.center
node.center          # Point(x, y) — handy for tap(node.center.x, node.center.y)
```

!!! warning "Узел — это снимок, а не хэндл"
    `node_id` валиден только в пределах своего дампа и никогда не возвращается на
    устройство. Чтобы подействовать на найденный узел, используй критерии
    (`click(Selector...)`) или `tap(node.center)` — «кликнуть по этому объекту-узлу»
    нельзя.

## Навигация

Навигация вниз не требует подготовки:

```python
for child in node.children: ...
for desc in node.descendants(): ...   # pre-order
for n in node.walk(): ...             # node + descendants
```

Навигация вверх (`parent`, `ancestors`) требует ссылок на родителей, которые
дерево строит **лениво** — только когда ты ищешь через `tree.find`/`find_all` или
вызываешь `tree.link()` явно. За дамп, который ты лишь сериализуешь, связывание не
оплачивается.

```python
node = tree.find(Selector.id("com.app:id/user"))   # this links the tree
node.parent                                          # UiNode | None
list(node.ancestors())                               # parent → ... → root
```

## Подсчёт / инспекция

```python
count = sum(1 for _ in tree.root.walk())
texts = [n.text for n in tree.root.walk() if n.text]
```

Скрипт `examples/inspect_ui.py` печатает компактное дерево — удобно для подбора
селекторов.

См. также: [Селекторы](selectors.md) и [Окна и диалоги](windows.md).
