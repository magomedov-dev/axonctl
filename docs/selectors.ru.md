# Селекторы


[`Selector`][axonctl.Selector] описывает, *какой* узел (или узлы) найти в
сдампленном дереве UI. Всё сопоставление выполняется на ПК поверх дампа (принцип
устройства без состояния), поэтому вы получаете богатый набор способов поиска —
точное совпадение, подстроку, regex, позиционный выбор и вложенность — без
обращений к устройству, кроме самого дампа.

## Фабрики

Предпочитайте фабрики «сырому» конструктору:

```python
from axonctl import Selector

Selector.id("com.app:id/login")        # by resourceId
Selector.text("Sign in")               # by visible text
Selector.text_contains("Signing")      # substring of text
Selector.desc("Profile photo")         # by contentDesc
Selector.cls("android.widget.EditText")  # by Android class
```

Сырая форма — `Selector(by=..., value=..., match=..., index=...)`, где `by` — это
`resourceId` / `text` / `class` / `contentDesc` (зеркалит `by` из протокола).

## Режимы совпадения

`match` управляет тем, как сравнивается `value`:

| режим | значение |
|------|---------|
| `exact` (по умолчанию) | равенство строки целиком |
| `contains` | подстрока |
| `regex` | совпадает **где угодно** (как Kotlin-regex агента); якорите через `^` / `$` |

```python
Selector.text("OK")                          # exact
Selector.text("Sign", match="contains")      # substring (same as text_contains)
Selector.text(r"^Item \d+$", match="regex")  # anchored full match
Selector.id(r"com\.app:id/row_\d+", match="regex")
```

## Index — выбор N-го совпадения

Когда совпадает несколько узлов, `index` выбирает один (отсчёт с 0):

```python
first_field = Selector.cls("android.widget.EditText", index=0)
second_field = Selector.cls("android.widget.EditText", index=1)
```

`find` возвращает совпадение по индексу (или первое, если `index` не задан);
`find_all` возвращает все совпадения (или список из одного элемента, если `index`
задан).

## `.within(...)` — найти X внутри Y

Ограничьте поиск потомками другого совпадения:

```python
ok_in_dialog = Selector.text("OK").within(Selector.id("com.app:id/confirm_dialog"))
row_title = Selector.id("com.app:id/title").within(Selector.cls("...RecyclerView"))
```

`.within(...)` вычисляется на ПК для **запросов** (`find`, `find_all`,
`wait_for`, `wait_gone`).

!!! warning "`.within(...)` и действия над узлами"
    **Действия** над узлами (`click`, `set_text`, ...) отправляют селектор агенту,
    который сопоставляет по «голым» критериям и **не может** выразить вложенность.
    Передача селектора с `.within(...)` в действие приводит к
    [`UnsupportedSelector`][axonctl.UnsupportedSelector] (а не к молчаливому
    действию по неверной цели). Чтобы действовать внутри области, используйте
    `window_id` для окна или диалога, более конкретный селектор либо
    `tap(node.center)` после `find`.

## Где вычисляются селекторы

- **Запросы** (`Device.find`, `Device.find_all`, `UiTree.find`, `Device.wait_*`)
  вычисляют селектор целиком — включая `match`, `index` и `.within(...)` — на ПК.
- **Действия** (`Device.click`, `set_text`, `scroll`, ...) отправляют `by` /
  `value` / `match` / `index` (и опциональный `window_id`) агенту, который заново
  ищет от свежего корня и выполняет действие. `.within(...)` здесь не
  поддерживается.

См. также: [Дерево UI](tree.md) и [Ожидания](waiting.md).
