# Инспектор UI

Вид текущего экрана устройства в стиле Appium Inspector — генерируется как один
самодостаточный HTML-файл, который открывается в любом браузере. Без сервера, без
внешних ресурсов.

[`Device.inspect`][axonctl.Device.inspect] снимает дамп **и** скриншот и пишет
страницу:

```python
await device.inspect("ui.html")            # PNG (чётко)
await device.inspect("ui.html", format="jpeg", quality=80)  # меньше файл
```

Открой `ui.html` в браузере. Ты получишь:

- **Скриншот** с кликабельными оверлеями элементов. Наведение подсвечивает самый
  маленький элемент под курсором; клик — выбирает его.
- **Навигируемое дерево** (связано с оверлеем в обе стороны): наведение на строку
  подсвечивает её бокс, клик — выбирает. Поле поиска фильтрует по id / text /
  class.
- **Атрибуты выбранного элемента** (class, resourceId, text, contentDesc,
  clickable/enabled/focused, bounds).
- **Готовые к копированию сниппеты [`Selector`][axonctl.Selector]** для элемента
  (`Selector.id(...)`, `Selector.text(...)`, `Selector.desc(...)`,
  `Selector.cls(..., index=...)`) — копирование в один клик.

Это самый быстрый способ подобрать нужный селектор для сценария.

!!! note
    Дамп и скриншот — активного окна / всего экрана. Bounds узлов абсолютны
    относительно экрана, поэтому оверлей совпадает со скриншотом. Скриншоты
    ограничены платформой (~1/сек); `inspect` делает один.

## Рендер из уже имеющихся данных

Рендерер — чистая функция, поэтому можно собрать страницу из дампа и картинки,
снятых самостоятельно (например, сохранённых из прогона):

```python
from axonctl import build_inspector_html

tree = await device.dump(compress=False)
png = await device.screenshot(format="png")
html = build_inspector_html(tree, png, image_mime="image/png")
open("ui.html", "w", encoding="utf-8").write(html)
```

См. также: [Селекторы](selectors.md), [Дерево UI](tree.md),
[Скриншоты](screenshots.md).
