"""Draw one city's whole temperature record as a single grid.

One column per year, one row per month. Read left to right and you see a century
of change; read top to bottom and you see a year. The contribution graph does the
same trick with weeks and weekdays, which is why it can carry this at all.

Colour is the departure from that city's own 1961-1990 average for that month, so
a January is only ever compared with other Januaries in the same place. That makes
Singapore and Moscow directly comparable despite one having a seasonal swing of
two degrees and the other of thirty.

This is a deliberate copy of the renderer in the jonsut/jonsut profile repo rather
than a shared import. Two public repos sharing a module means a change made for
one silently breaks the other, and that repo is a personal profile page that has
to fail soft.
"""

FONT = ('-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", '
        "Helvetica, Arial, sans-serif")
TEAL, CORAL, NEUTRAL = "#3f8b92", "#fc4b34", "#8c9196"

# Fixed across every city, because the whole point is that they compare. Bands are
# in degrees against the city's own baseline, not percentiles of its own spread,
# which would flatten a fast-warming city into looking like a stable one.
CUTS = [-1.5, -0.5, 0.5, 1.5]
HUES = [TEAL, TEAL, NEUTRAL, CORAL, CORAL]
ALPHA = [0.75, 0.34, 0.15, 0.34, 0.75]

W, PAD, GUTTER = 900, 16, 30
CELL, GAP, RADIUS = 7, 2, 2
STEP = CELL + GAP
HEAD_H = 34
HEAD_SIZE = 16
GRID_X = PAD + GUTTER
MONTH_LABELS = {0: "Jan", 3: "Apr", 6: "Jul", 9: "Oct"}
DECADE = 10

ICON_BOX, ICON_SIZE, ICON_GAP = 24, 19, 8
CAP = 0.72
HEAD_BASE = HEAD_H - 12
ICON_Y = HEAD_BASE - CAP * HEAD_SIZE / 2 - ICON_SIZE / 2
TEXT_X = ICON_SIZE + ICON_GAP
# Icon from Unicons by Iconscout, under the IconScout Simple License. Left with its
# fill="currentColor" intact and coloured through the `color` property, so the
# vendor path data is unmodified.
THERMOMETER = (
    '<!-- Icon from Unicons by Iconscout - '
    'https://github.com/Iconscout/unicons/blob/master/LICENSE -->'
    '<path fill="currentColor" d="M13 15.28V5.5a1 1 0 0 0-2 0v9.78A2 2 0 0 0 10 17a2 '
    '2 0 0 0 4 0a2 2 0 0 0-1-1.72M16.5 13V5.5a4.5 4.5 0 0 0-9 0V13a6 6 0 0 0 3.21 '
    '9.83A7 7 0 0 0 12 23a6 6 0 0 0 4.5-10m-2 7.07a4 4 0 0 1-6.42-2.2a4 4 0 0 1 '
    '1.1-3.76a1 1 0 0 0 .3-.71V5.5a2.5 2.5 0 0 1 5 0v7.94a1 1 0 0 0 .3.71a4 4 0 0 '
    '1-.28 6Z"/>')


def band(value):
    return next((i for i, cut in enumerate(CUTS) if value < cut), len(CUTS))


def render(city, series, first, last, head, note, path):
    """series maps (year, month) to an anomaly in degrees. Months not in it are void."""
    ns = "".join(ch for ch in city.lower() if ch.isalpha())
    years = list(range(first, last + 1))
    scale = ICON_SIZE / ICON_BOX
    parts = [
        f'<g class="icon" transform="translate(0 {ICON_Y:.2f}) '
        f'scale({scale:.6f})">{THERMOMETER}</g>',
        f'<text class="head" x="{TEXT_X}" y="{HEAD_BASE}">'
        f'<tspan class="strong">{city}.</tspan>&#160;{head}</text>',
    ]

    card_top = HEAD_H
    y = card_top + PAD + 12
    for i, year in enumerate(years):
        if year % DECADE == 0:
            parts.append(f'<text class="axis" x="{GRID_X + i * STEP}" '
                         f'y="{y}">{year}</text>')
    y += 10

    for row, text in MONTH_LABELS.items():
        parts.append(f'<text class="axis end" x="{GRID_X - 8}" '
                     f'y="{y + row * STEP + CELL}">{text}</text>')

    for i, year in enumerate(years):
        for month in range(12):
            value = series.get((year, month + 1))
            cls = f"{ns}-void" if value is None else f"{ns}{band(value)}"
            parts.append(f'<rect class="{cls}" x="{GRID_X + i * STEP}" '
                         f'y="{y + month * STEP}" width="{CELL}" height="{CELL}" '
                         f'rx="{RADIUS}"/>')

    foot = y + 12 * STEP - GAP + 20
    parts.append(f'<text class="note" x="{GRID_X}" y="{foot}">{note}</text>')
    sw = len(HUES) * (CELL + 3)
    lx = W - PAD - sw - (len("Warmer") * 6.6 + 3)
    parts.append(f'<text class="note end" x="{lx - 6:.1f}" y="{foot}">Cooler</text>')
    for i in range(len(HUES)):
        parts.append(f'<rect class="{ns}{i}" x="{lx + i * (CELL + 3):.1f}" '
                     f'y="{foot - CELL + 1}" width="{CELL}" height="{CELL}" '
                     f'rx="{RADIUS}"/>')
    parts.append(f'<text class="note" x="{lx + sw + 3:.1f}" y="{foot}">Warmer</text>')

    card_bottom = foot + PAD
    parts.insert(2, f'<rect class="card" x="0.5" y="{card_top + 0.5}" '
                    f'width="{W - 1}" height="{card_bottom - card_top}" rx="6"/>')
    height = card_bottom + 2

    # Class names are namespaced per city. CSS inside an SVG is document-global, so
    # if these are ever inlined together rather than loaded as images, the last
    # stylesheet would otherwise repaint every plate on the page.
    style = (f"text {{ font-family: {FONT}; }}\n"
             f".head {{ font-size: {HEAD_SIZE}px; fill: #1f2328; }}\n"
             ".strong { font-weight: 600; }\n"
             ".icon { color: #1f2328; }\n"
             ".axis { font-size: 11px; fill: #1f2328; }\n"
             ".note { font-size: 12px; fill: #59636e; }\n"
             ".end { text-anchor: end; }\n"
             ".card { fill: none; stroke: #d1d9e0; stroke-width: 1; }\n"
             f".{ns}-void {{ fill: {NEUTRAL}; fill-opacity: 0.10; }}\n")
    for i, colour in enumerate(HUES):
        style += f".{ns}{i} {{ fill: {colour}; fill-opacity: {ALPHA[i]:.2f}; }}\n"
    style += ("@media (prefers-color-scheme: dark) {\n"
              "  .head, .axis { fill: #f0f6fc; }\n"
              "  .icon { color: #f0f6fc; }\n"
              "  .note { fill: #9198a1; }\n"
              "  .card { stroke: #3d444d; }\n"
              "}\n")

    label = f"{city}. {head}. {note}."
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" '
           f'width="{W}" height="{height}" role="img" aria-label="{label}">\n'
           f"<title>{city}</title>\n<style>{style}</style>\n"
           + "\n".join(parts) + "\n</svg>\n")
    open(path, "w").write(svg)
    return height
