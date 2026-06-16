"""Interactive UI inspector.

Render a single self-contained HTML file from a dump and a screenshot: the
screenshot with clickable element overlays, a navigable tree, the selected
element's attributes, and ready-to-copy :class:`~axonctl.Selector` snippets — an
Appium-Inspector-style view you open straight in a browser, no server.

The renderer (:func:`build_inspector_html`) is pure: ``(tree, screenshot) -> str``.
:meth:`axonctl.Device.inspect` captures both and writes the file.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import orjson

if TYPE_CHECKING:
    from .tree.node import UiNode
    from .tree.tree import UiTree


def _flatten(root: UiNode) -> list[dict[str, Any]]:
    """Walk the tree pre-order into a flat list of plain dicts for the HTML."""
    nodes: list[dict[str, Any]] = []
    class_counts: dict[str | None, int] = {}

    def walk(node: UiNode, depth: int, parent: int | None) -> None:
        index = len(nodes)
        bounds = (
            None
            if node.bounds is None
            else {
                "l": node.bounds.left,
                "t": node.bounds.top,
                "r": node.bounds.right,
                "b": node.bounds.bottom,
            }
        )
        class_index = class_counts.get(node.class_name, 0)
        class_counts[node.class_name] = class_index + 1
        nodes.append(
            {
                "i": index,
                "depth": depth,
                "parent": parent,
                "cls": node.class_name,
                "text": node.text,
                "rid": node.resource_id,
                "desc": node.content_desc,
                "clickable": node.clickable,
                "enabled": node.enabled,
                "focused": node.focused,
                "bounds": bounds,
                "clsIndex": class_index,
            }
        )
        for child in node.children:
            walk(child, depth + 1, index)

    walk(root, 0, None)
    return nodes


def _frame(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """Coordinate frame for the overlay: the root bounds, or the union of all."""
    root_bounds = nodes[0]["bounds"] if nodes else None
    if root_bounds is not None:
        return dict(root_bounds)
    boxes = [n["bounds"] for n in nodes if n["bounds"] is not None]
    if not boxes:
        return {"l": 0, "t": 0, "r": 1, "b": 1}
    return {
        "l": min(b["l"] for b in boxes),
        "t": min(b["t"] for b in boxes),
        "r": max(b["r"] for b in boxes),
        "b": max(b["b"] for b in boxes),
    }


def build_inspector_html(
    tree: UiTree,
    screenshot: bytes,
    *,
    image_mime: str = "image/png",
    image_size: tuple[int, int] | None = None,
    title: str = "axonctl inspector",
) -> str:
    """Render a self-contained inspector HTML page.

    Args:
        tree: The parsed UI dump to overlay.
        screenshot: The screen image bytes (embedded as a data URI).
        image_mime: MIME type of ``screenshot`` (e.g. ``"image/png"`` or
            ``"image/jpeg"``).
        image_size: ``(width, height)`` of the screenshot in pixels. Node bounds
            are screen-absolute, so this is the correct overlay frame; when
            omitted, the root/union bounds are used as a fallback.
        title: Document title.

    Returns:
        A complete HTML document as a string (no external dependencies).
    """
    nodes = _flatten(tree.root)
    if image_size is not None and image_size[0] > 0 and image_size[1] > 0:
        frame = {"l": 0, "t": 0, "r": image_size[0], "b": image_size[1]}
    else:
        frame = _frame(nodes)
    payload = {
        "package": tree.package,
        "screen": tree.screen,
        "frame": frame,
        "nodes": nodes,
    }
    data_json = orjson.dumps(payload).decode("utf-8")
    img_b64 = base64.b64encode(screenshot).decode("ascii")
    subtitle = f"{tree.package} · screen {tree.screen} · {len(nodes)} elements"
    return (
        _TEMPLATE.replace("{{TITLE}}", _esc(title))
        .replace("{{SUBTITLE}}", _esc(subtitle))
        .replace("{{MIME}}", image_mime)
        .replace("{{IMG}}", img_b64)
        .replace("{{DATA}}", data_json)
    )


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  :root {
    --bg: #0f1117; --panel: #171a23; --line: #262b38; --text: #e6e8ee;
    --muted: #8b93a7; --accent: #6366f1; --accent-soft: rgba(99,102,241,.18);
    --hover: #f59e0b; --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    font: 14px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: var(--bg); color: var(--text); display: flex; flex-direction: column;
  }
  header {
    display: flex; align-items: center; gap: 16px; padding: 10px 16px;
    border-bottom: 1px solid var(--line); background: var(--panel);
  }
  header .title { font-weight: 600; }
  header .sub { color: var(--muted); font-size: 12px; }
  header .spacer { flex: 1; }
  #search {
    width: 280px; padding: 7px 10px; border: 1px solid var(--line); border-radius: 8px;
    background: var(--bg); color: var(--text); font-size: 13px; outline: none;
  }
  #search:focus { border-color: var(--accent); }
  main { flex: 1; display: flex; min-height: 0; }
  #stage {
    flex: 1; display: flex; align-items: center; justify-content: center;
    overflow: auto; padding: 16px;
    background:
      linear-gradient(45deg, #12141c 25%, transparent 25%) 0 0/22px 22px,
      linear-gradient(-45deg, #12141c 25%, transparent 25%) 0 0/22px 22px;
  }
  #wrap { position: relative; display: inline-block; line-height: 0; box-shadow: 0 8px 40px rgba(0,0,0,.5); }
  #shot { display: block; max-height: calc(100vh - 120px); width: auto; border-radius: 4px; }
  #overlay { position: absolute; inset: 0; }
  .box { position: absolute; pointer-events: none; border: 1.5px solid transparent; border-radius: 2px; }
  #hover { border-color: var(--hover); background: rgba(245,158,11,.12); }
  #sel { border-color: var(--accent); background: var(--accent-soft); }
  aside {
    width: 430px; border-left: 1px solid var(--line); background: var(--panel);
    display: flex; flex-direction: column; min-height: 0;
  }
  #tree { flex: 1; overflow: auto; padding: 6px 0; }
  .row {
    padding: 3px 12px; white-space: nowrap; cursor: pointer; font-size: 13px;
    overflow: hidden; text-overflow: ellipsis; border-left: 2px solid transparent;
  }
  .row:hover { background: rgba(255,255,255,.04); }
  .row.sel { background: var(--accent-soft); border-left-color: var(--accent); }
  .row .tag { color: var(--muted); }
  .row .id { color: #7dd3fc; }
  .row .txt { color: #a7f3d0; }
  #details {
    border-top: 1px solid var(--line); max-height: 46%; overflow: auto; padding: 12px 14px;
  }
  #details .empty { color: var(--muted); }
  #details h3 { margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
  table.attrs { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  table.attrs td { padding: 3px 4px; vertical-align: top; border-bottom: 1px solid var(--line); }
  table.attrs td.k { color: var(--muted); width: 96px; }
  table.attrs td.v { font-family: var(--mono); word-break: break-all; }
  .sel-line {
    display: flex; align-items: center; gap: 8px; margin: 6px 0;
    font-family: var(--mono); font-size: 12.5px;
  }
  .sel-line code {
    flex: 1; background: var(--bg); border: 1px solid var(--line); border-radius: 6px;
    padding: 5px 8px; overflow: auto; white-space: pre;
  }
  .copy {
    border: 1px solid var(--line); background: var(--bg); color: var(--muted);
    border-radius: 6px; padding: 5px 9px; cursor: pointer; font-size: 12px;
  }
  .copy:hover { color: var(--text); border-color: var(--accent); }
  .copy.ok { color: #34d399; border-color: #34d399; }
</style>
</head>
<body>
<header>
  <div>
    <div class="title">{{TITLE}}</div>
    <div class="sub">{{SUBTITLE}}</div>
  </div>
  <div class="spacer"></div>
  <input id="search" type="search" placeholder="Filter by id / text / class…" autocomplete="off">
</header>
<main>
  <div id="stage">
    <div id="wrap">
      <img id="shot" src="data:{{MIME}};base64,{{IMG}}" alt="screenshot">
      <div id="overlay">
        <div id="hover" class="box"></div>
        <div id="sel" class="box"></div>
      </div>
    </div>
  </div>
  <aside>
    <div id="tree"></div>
    <div id="details"><div class="empty">Hover the screenshot or pick a node to inspect.</div></div>
  </aside>
</main>
<script>
const D = {{DATA}};
const NODES = D.nodes, FRAME = D.frame;
const FW = FRAME.r - FRAME.l, FH = FRAME.b - FRAME.t;
const shot = document.getElementById('shot');
const hoverBox = document.getElementById('hover');
const selBox = document.getElementById('sel');
const treeEl = document.getElementById('tree');
const detailsEl = document.getElementById('details');
const searchEl = document.getElementById('search');
let selectedIndex = null;

const area = b => (b.r - b.l) * (b.b - b.t);
function place(el, b) {
  if (!b) { el.style.display = 'none'; return; }
  el.style.display = 'block';
  el.style.left = ((b.l - FRAME.l) / FW * 100) + '%';
  el.style.top = ((b.t - FRAME.t) / FH * 100) + '%';
  el.style.width = ((b.r - b.l) / FW * 100) + '%';
  el.style.height = ((b.b - b.t) / FH * 100) + '%';
}
function nodeAt(x, y) {
  let best = null;
  for (const n of NODES) {
    const b = n.bounds;
    if (!b) continue;
    if (x >= b.l && x <= b.r && y >= b.t && y <= b.b) {
      if (best === null || area(b) <= area(best.bounds)) best = n;
    }
  }
  return best;
}
function shortClass(c) { return c ? c.split('.').pop() : 'node'; }
function esc(s) { return (s ?? '').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }
function q(s) { return JSON.stringify(s ?? ''); }

function selectorsFor(n) {
  const out = [];
  if (n.rid) out.push('Selector.id(' + q(n.rid) + ')');
  if (n.text) out.push('Selector.text(' + q(n.text) + ')');
  if (n.desc) out.push('Selector.desc(' + q(n.desc) + ')');
  if (n.cls) out.push('Selector.cls(' + q(n.cls) + ', index=' + n.clsIndex + ')');
  return out;
}

// --- tree ---
const rows = [];
for (const n of NODES) {
  const row = document.createElement('div');
  row.className = 'row';
  row.style.paddingLeft = (12 + n.depth * 14) + 'px';
  row.dataset.i = n.i;
  let html = '<span class="tag">' + esc(shortClass(n.cls)) + '</span>';
  if (n.rid) html += ' <span class="id">#' + esc(n.rid.split('/').pop()) + '</span>';
  if (n.text) html += ' <span class="txt">“' + esc(n.text) + '”</span>';
  row.innerHTML = html;
  row.addEventListener('mouseenter', () => place(hoverBox, n.bounds));
  row.addEventListener('mouseleave', () => place(hoverBox, null));
  row.addEventListener('click', () => select(n.i));
  treeEl.appendChild(row);
  rows.push(row);
}

function select(i) {
  selectedIndex = i;
  const n = NODES[i];
  place(selBox, n ? n.bounds : null);
  rows.forEach(r => r.classList.toggle('sel', +r.dataset.i === i));
  const sel = rows[i];
  if (sel) sel.scrollIntoView({ block: 'nearest' });
  renderDetails(n);
}

function renderDetails(n) {
  if (!n) { detailsEl.innerHTML = '<div class="empty">No element.</div>'; return; }
  const attrs = [
    ['class', n.cls], ['resourceId', n.rid], ['text', n.text], ['contentDesc', n.desc],
    ['clickable', n.clickable], ['enabled', n.enabled], ['focused', n.focused],
    ['bounds', n.bounds ? `[${n.bounds.l},${n.bounds.t}][${n.bounds.r},${n.bounds.b}]` : null],
  ];
  let h = '<h3>Attributes</h3><table class="attrs">';
  for (const [k, v] of attrs) {
    if (v === null || v === undefined || v === '') continue;
    h += '<tr><td class="k">' + k + '</td><td class="v">' + esc(String(v)) + '</td></tr>';
  }
  h += '</table>';
  const sels = selectorsFor(n);
  if (sels.length) {
    h += '<h3 style="margin-top:14px">Selectors</h3>';
    for (const s of sels) {
      h += '<div class="sel-line"><code>' + esc(s) + '</code>' +
           '<button class="copy" data-c="' + esc(s) + '">copy</button></div>';
    }
  }
  detailsEl.innerHTML = h;
  detailsEl.querySelectorAll('.copy').forEach(btn => {
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(btn.dataset.c).then(() => {
        btn.textContent = 'copied'; btn.classList.add('ok');
        setTimeout(() => { btn.textContent = 'copy'; btn.classList.remove('ok'); }, 1000);
      });
    });
  });
}

// --- screenshot interaction ---
function frameCoords(e) {
  const r = shot.getBoundingClientRect();
  return [
    FRAME.l + (e.clientX - r.left) / r.width * FW,
    FRAME.t + (e.clientY - r.top) / r.height * FH,
  ];
}
shot.addEventListener('mousemove', e => {
  const [x, y] = frameCoords(e);
  const n = nodeAt(x, y);
  place(hoverBox, n ? n.bounds : null);
});
shot.addEventListener('mouseleave', () => place(hoverBox, null));
shot.addEventListener('click', e => {
  const [x, y] = frameCoords(e);
  const n = nodeAt(x, y);
  if (n) select(n.i);
});

// --- search ---
searchEl.addEventListener('input', () => {
  const q = searchEl.value.toLowerCase();
  for (let i = 0; i < NODES.length; i++) {
    const n = NODES[i];
    const hay = ((n.rid || '') + ' ' + (n.text || '') + ' ' + (n.desc || '') + ' ' + (n.cls || '')).toLowerCase();
    rows[i].style.display = !q || hay.includes(q) ? '' : 'none';
  }
});
</script>
</body>
</html>
"""
