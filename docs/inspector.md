# UI inspector

An Appium-Inspector-style view of a device's current screen — generated as a
single self-contained HTML file you open in any browser. No server, no external
assets.

[`Device.inspect`][axonctl.Device.inspect] captures a dump **and** a screenshot
and writes the page:

```python
await device.inspect("ui.html")            # PNG (crisp)
await device.inspect("ui.html", format="jpeg", quality=80)  # smaller file
```

Open `ui.html` in a browser. You get:

- **The screenshot** with clickable element overlays. Hover to highlight the
  smallest element under the cursor; click to select it.
- **A navigable tree** (left↔right linked with the overlay): hover a row to
  highlight its box, click to select. A search box filters by id / text / class.
- **The selected element's attributes** (class, resourceId, text, contentDesc,
  clickable/enabled/focused, bounds).
- **Ready-to-copy [`Selector`][axonctl.Selector] snippets** for that element
  (`Selector.id(...)`, `Selector.text(...)`, `Selector.desc(...)`,
  `Selector.cls(..., index=...)`) — one click to copy.

It is the fastest way to discover the right selector for a scenario.

!!! note
    The dump and screenshot are of the active window / full screen. Node bounds
    are screen-absolute, so the overlay lines up with the screenshot. Screenshots
    are rate-limited (~1/sec) by the platform; `inspect` takes a single one.

## Rendering from data you already have

The renderer is a pure function, so you can build the page from a dump and image
you captured yourself (e.g. saved from a run):

```python
from axonctl import build_inspector_html

tree = await device.dump(compress=False)
png = await device.screenshot(format="png")
html = build_inspector_html(tree, png, image_mime="image/png")
open("ui.html", "w", encoding="utf-8").write(html)
```

See also: [Selectors](selectors.md), [The UI tree](tree.md),
[Screenshots](screenshots.md).
