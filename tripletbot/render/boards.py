"""Board/grid drawing helpers used by every game."""
from __future__ import annotations

from typing import Sequence

from PIL import ImageDraw

from . import theme as T

Rect = tuple[float, float, float, float]


def mid(rect: Sequence[float]) -> tuple[float, float]:
    return ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)


def width(rect: Sequence[float]) -> float:
    return rect[2] - rect[0]


def height(rect: Sequence[float]) -> float:
    return rect[3] - rect[1]


def fit(box: Rect, w: float, h: float, anchor: str = "center") -> Rect:
    bx0, by0, bx1, by1 = box
    x0 = bx0 + ((bx1 - bx0) - w) / 2
    y0 = by0 + ((by1 - by0) - h) / 2
    if anchor == "top":
        y0 = by0
    elif anchor == "bottom":
        y0 = by1 - h
    return (x0, y0, x0 + w, y0 + h)


def square(box: Rect, pad: float = 0) -> Rect:
    bx0, by0, bx1, by1 = box
    bx0 += pad
    by0 += pad
    bx1 -= pad
    by1 -= pad
    side = min(bx1 - bx0, by1 - by0)
    return ((bx0 + bx1 - side) / 2, (by0 + by1 - side) / 2, (bx0 + bx1 + side) / 2, (by0 + by1 + side) / 2)


def grid(box: Rect, cols: int, rows: int, gap: float = 8, square_cells: bool = True) -> list[Rect]:
    bx0, by0, bx1, by1 = box
    cw = ((bx1 - bx0) - gap * (cols - 1)) / cols
    ch = ((by1 - by0) - gap * (rows - 1)) / rows
    if square_cells:
        cw = ch = min(cw, ch)
    total_w = cw * cols + gap * (cols - 1)
    total_h = ch * rows + gap * (rows - 1)
    x0 = bx0 + ((bx1 - bx0) - total_w) / 2
    y0 = by0 + ((by1 - by0) - total_h) / 2
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append((x0 + c * (cw + gap), y0 + r * (ch + gap), x0 + c * (cw + gap) + cw, y0 + r * (ch + gap) + ch))
    return out


def cell(
    f,
    rect: Rect,
    fill: tuple | None = None,
    outline: tuple | None = None,
    radius: int = 12,
    width: int = 2,
    shadow: bool = False,
) -> None:
    d = f.d
    if shadow:
        sh = (rect[0] + 2, rect[1] + 4, rect[2] + 2, rect[3] + 4)
        d.rounded_rectangle(sh, radius=radius, fill=(6, 8, 12))
    d.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def hatch(d: ImageDraw.ImageDraw, rect: Rect, color: tuple, step: int = 14, width: int = 1) -> None:
    x0, y0, x1, y1 = rect
    x = x0 - (y1 - y0)
    while x < x1:
        d.line((x, y1, x + (y1 - y0), y0), fill=color, width=width)
        x += step


def grid_lines(d: ImageDraw.ImageDraw, rect: Rect, cols: int, rows: int, color: tuple = T.LINE) -> None:
    x0, y0, x1, y1 = rect
    for c in range(1, cols):
        x = x0 + (x1 - x0) * c / cols
        d.line((x, y0, x, y1), fill=color, width=1)
    for r in range(1, rows):
        y = y0 + (y1 - y0) * r / rows
        d.line((x0, y, x1, y), fill=color, width=1)


def title(f, xy, s, size=15, color=T.DIM) -> None:
    f.text(xy, s.upper(), size, color, bold=True)


def badge(f, center, r, s, fg=T.TEXT, bg=T.CARD_HI, size=None) -> None:
    cx, cy = center
    f.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg)
    f.text((cx, cy + 1), s, size or int(r * 1.1), fg, bold=True, anchor="mm")


def panel_label(f, xy, s, color=T.DIM, size=13) -> None:
    f.text(xy, s.upper(), size, color, bold=True)
