"""TripleTBot visual language.

Everything the bot posts is a real rendered frame (Pillow), never an ASCII board.
This module owns the palette, typography, cards, pills, avatars and gradients that
every game reuses so the whole arcade looks like one product.
"""
from __future__ import annotations

import io
import math
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "assets" / "fonts"

# ---------------------------------------------------------------- canvas size
W, H = 1100, 720

# -------------------------------------------------------------------- palette
BG_TOP = (17, 20, 30)
BG_BOTTOM = (8, 10, 15)
CARD = (23, 27, 38)
CARD_HI = (31, 37, 51)
CARD_LO = (18, 21, 30)
LINE = (47, 55, 74)
LINE_SOFT = (36, 43, 58)
TEXT = (233, 238, 248)
MUTED = (147, 159, 182)
DIM = (99, 110, 132)

ACCENT = (124, 92, 255)          # violet
ACCENT2 = (34, 211, 238)         # cyan
ACCENT_GRAD = (ACCENT, ACCENT2)
GOLD = (255, 199, 84)
GREEN = (52, 211, 153)
RED = (248, 113, 113)
BLUE = (96, 165, 250)
PINK = (244, 114, 182)
ORANGE = (251, 146, 60)
PURPLE = (167, 139, 250)

# player accent colours, one per seat
SEAT_COLORS = [
    (124, 92, 255),   # violet
    (34, 211, 238),   # cyan
    (255, 199, 84),   # gold
    (244, 114, 182),  # pink
]
SEAT_COLORS_DARK = [
    (74, 49, 170),
    (14, 116, 144),
    (150, 108, 24),
    (150, 55, 105),
]


# ------------------------------------------------------------------ typography
_FONT_CANDIDATES = {
    (False, False): ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    (True, False): ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    (False, True): ["DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"],
    (True, True): ["DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"],
}


@lru_cache(maxsize=256)
def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    for cand in _FONT_CANDIDATES[(bold, mono)]:
        path = Path(cand)
        if not path.is_absolute():
            path = FONT_DIR / cand
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


@lru_cache(maxsize=4096)
def measure(s: str, size: int, bold: bool = False, mono: bool = False) -> tuple[int, int]:
    f = font(size, bold, mono)
    if not s:
        return (0, size)
    box = f.getbbox(s)
    return (box[2] - box[0], box[3] - box[1])


def text(
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    s: str,
    size: int = 20,
    color: tuple = TEXT,
    bold: bool = False,
    anchor: str = "la",
    mono: bool = False,
    stroke: int = 0,
    stroke_fill: tuple | None = None,
) -> tuple[int, int]:
    d.text(
        (round(xy[0]), round(xy[1])),
        s,
        font=font(size, bold, mono),
        fill=color,
        anchor=anchor,
        stroke_width=stroke,
        stroke_fill=stroke_fill or (0, 0, 0),
    )
    return measure(s, size, bold, mono)


def ellipsize(s: str, size: int, max_w: int, bold: bool = False, mono: bool = False) -> str:
    if measure(s, size, bold, mono)[0] <= max_w:
        return s
    out = s
    while out and measure(out + "…", size, bold, mono)[0] > max_w:
        out = out[:-1]
    return (out + "…") if out else "…"


def wrap(s: str, size: int, max_w: int, bold: bool = False, max_lines: int = 99) -> list[str]:
    words = s.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if measure(trial, size, bold)[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and lines:
        joined = " ".join(lines)
        if measure(joined, size, bold)[0] > max_w or len(" ".join(words)) > len(joined):
            lines[-1] = ellipsize(lines[-1] + " …", size, max_w, bold)
    return lines


def block(
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    s: str,
    size: int = 18,
    color: tuple = MUTED,
    bold: bool = False,
    max_w: int = 200,
    leading: float = 1.35,
    max_lines: int = 99,
) -> int:
    """Draw wrapped text, return the y coordinate after the last line."""
    y = xy[1]
    for line in wrap(s, size, max_w, bold, max_lines):
        text(d, (xy[0], y), line, size, color, bold)
        y += round(size * leading)
    return y


# ------------------------------------------------------------------- surfaces
def gradient(size: tuple[int, int], c1: tuple, c2: tuple, vertical: bool = True) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h) if vertical else (w, 1))
    d = ImageDraw.Draw(base)
    n = h if vertical else w
    for i in range(n):
        t = i / max(1, n - 1)
        col = tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))
        if vertical:
            d.point((0, i), fill=col)
        else:
            d.point((i, 0), fill=col)
    return base.resize((w, h), Image.BILINEAR)


def _hexdot_layer(size: tuple[int, int], spacing: int = 26, radius: int = 1) -> Image.Image:
    layer = Image.new("L", size, 0)
    d = ImageDraw.Draw(layer)
    for y in range(0, size[1], spacing):
        for x in range(0, size[0], spacing):
            d.ellipse((x, y, x + radius, y + radius), fill=26)
    return layer


@lru_cache(maxsize=4)
def background() -> Image.Image:
    img = gradient((W, H), BG_TOP, BG_BOTTOM).convert("RGB")
    dots = _hexdot_layer((W, H))
    img.paste((38, 44, 60), (0, 0), dots)
    # soft accent blooms in the corners
    bloom = Image.new("RGB", (W, H), (0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    bd.ellipse((-180, -240, 420, 240), fill=(34, 22, 70))
    bd.ellipse((W - 420, H - 260, W + 180, H + 240), fill=(6, 34, 46))
    bloom = bloom.filter(ImageFilter.GaussianBlur(120))
    img = ImageChops.add(img, bloom)
    # top hairline
    accent = gradient((W, 3), ACCENT, ACCENT2, vertical=False)
    img.paste(accent, (0, 0))
    return img


def card(
    img: Image.Image,
    d: ImageDraw.ImageDraw,
    box: tuple,
    radius: int = 18,
    fill: tuple = CARD,
    outline: tuple | None = LINE_SOFT,
    width: int = 2,
    shadow: int = 14,
) -> None:
    if shadow:
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rounded_rectangle(box, radius=radius, fill=min(160, shadow * 9))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        img.paste((2, 3, 6), (0, 0), sh)
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def inset(
    d: ImageDraw.ImageDraw,
    box: tuple,
    radius: int = 14,
    fill: tuple = CARD_LO,
    outline: tuple | None = LINE_SOFT,
    width: int = 1,
) -> None:
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def glow_box(
    img: Image.Image,
    d: ImageDraw.ImageDraw,
    box: tuple,
    color: tuple,
    radius: int = 14,
    width: int = 3,
    blur: int = 10,
) -> None:
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, outline=color, width=width + 2)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste(ImageChops.add(img, layer))
    d.rounded_rectangle(box, radius=radius, outline=color, width=width)


def pill(
    img: Image.Image,
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    s: str,
    size: int = 16,
    fg: tuple = TEXT,
    bg: tuple = CARD_HI,
    bold: bool = True,
    padx: int = 12,
    pady: int = 7,
    outline: tuple | None = None,
    anchor_right: bool = False,
    icon: str = "",
) -> tuple[int, int, int, int]:
    label = (icon + " " + s).strip() if icon else s
    tw, th = measure(label, size, bold)
    w = tw + padx * 2
    h = th + pady * 2 + 2
    x = xy[0] - w if anchor_right else xy[0]
    box = (x, xy[1], x + w, xy[1] + h)
    d.rounded_rectangle(box, radius=h // 2, fill=bg, outline=outline, width=1)
    text(d, (x + w / 2, xy[1] + h / 2), label, size, fg, bold, anchor="mm")
    return box


def divider(d: ImageDraw.ImageDraw, x0: float, y: float, x1: float, color: tuple = LINE_SOFT) -> None:
    d.line((x0, y, x1, y), fill=color, width=1)


# --------------------------------------------------------------------- avatars
def _initials(name: str) -> str:
    parts = [p for p in name.replace("_", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


@lru_cache(maxsize=128)
def _avatar_image(data: bytes, size: int) -> Image.Image | None:
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2, (w - side) // 2 + side, (h - side) // 2 + side))
    return im.resize((size, size), Image.LANCZOS)


def avatar(
    img: Image.Image,
    d: ImageDraw.ImageDraw,
    center: tuple[float, float],
    radius: int,
    name: str,
    color: tuple = ACCENT,
    data: bytes | None = None,
    ring: int = 3,
    dim: bool = False,
) -> None:
    cx, cy = center
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    ss = radius * 2
    src = _avatar_image(data, ss) if data else None
    if src is not None:
        mask = Image.new("L", (ss, ss), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, ss - 1, ss - 1), fill=255)
        img.paste(src, (round(box[0]), round(box[1])), mask)
    else:
        d.ellipse(box, fill=tuple(round(c * 0.32) for c in color))
        text(d, (cx, cy + 1), _initials(name), max(11, int(radius * 0.78)), tuple(min(255, c + 90) for c in color), True, anchor="mm")
    d.ellipse(box, outline=color if not dim else LINE, width=ring)


# --------------------------------------------------------------------- pieces
def ring(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, width: int = 6) -> None:
    d.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), outline=color, width=width)


def disc(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, shade: bool = True) -> None:
    d.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=color)
    if shade:
        hl = tuple(min(255, c + 55) for c in color)
        d.ellipse((center[0] - r * 0.55, center[1] - r * 0.72, center[0] + r * 0.18, center[1] - r * 0.12), fill=hl)


def cross(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, width: int = 8) -> None:
    cx, cy = center
    d.line((cx - r, cy - r, cx + r, cy + r), fill=color, width=width)
    d.line((cx - r, cy + r, cx + r, cy - r), fill=color, width=width)


def diamond(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, outline: tuple | None = None) -> None:
    cx, cy = center
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    d.polygon(pts, fill=color, outline=outline)


def star(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, points: int = 5) -> None:
    cx, cy = center
    pts = []
    for i in range(points * 2):
        rad = r if i % 2 == 0 else r * 0.45
        ang = -math.pi / 2 + i * math.pi / points
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=color)


def check(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, width: int = 7) -> None:
    cx, cy = center
    d.line((cx - r, cy, cx - r * 0.15, cy + r * 0.75), fill=color, width=width, joint="curve")
    d.line((cx - r * 0.15, cy + r * 0.75, cx + r, cy - r * 0.7), fill=color, width=width, joint="curve")


def arrow(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple, direction: str = "right", width: int = 5) -> None:
    cx, cy = center
    ang = {"right": 0, "down": 90, "left": 180, "up": 270}[direction]
    a = math.radians(ang)
    tip = (cx + r * math.cos(a), cy + r * math.sin(a))
    left = (cx - r * 0.55 * math.cos(a) - r * 0.75 * math.sin(a), cy - r * 0.55 * math.sin(a) + r * 0.75 * math.cos(a))
    right = (cx - r * 0.55 * math.cos(a) + r * 0.75 * math.sin(a), cy - r * 0.55 * math.sin(a) - r * 0.75 * math.cos(a))
    d.line((left, tip), fill=color, width=width)
    d.line((right, tip), fill=color, width=width)


def rounded_progress(
    d: ImageDraw.ImageDraw,
    box: tuple,
    pct: float,
    color: tuple,
    track: tuple = (39, 46, 62),
    radius: int = 6,
) -> None:
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=radius, fill=track)
    pct = max(0.0, min(1.0, pct))
    if pct <= 0:
        return
    w = max(radius * 2, (x1 - x0) * pct)
    d.rounded_rectangle((x0, y0, x0 + w, y1), radius=radius, fill=color)


def logo(img: Image.Image, d: ImageDraw.ImageDraw, box: tuple, label: str = "TT", size: int = 48) -> None:
    x0, y0, x1, y1 = box
    grad = gradient((x1 - x0, y1 - y0), ACCENT, ACCENT2, vertical=False)
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=int((y1 - y0) * 0.32), fill=255)
    img.paste(grad, (x0, y0), mask)
    text(d, ((x0 + x1) / 2, (y0 + y1) / 2 + 1), label, size, (12, 14, 22), True, anchor="mm")


def trophy(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float, color: tuple = GOLD) -> None:
    cx, cy = center
    d.rounded_rectangle((cx - r * 0.55, cy - r, cx + r * 0.55, cy + r * 0.15), radius=int(r * 0.25), fill=color)
    d.arc((cx - r * 1.05, cy - r * 0.85, cx - r * 0.35, cy + r * 0.1), 90, 270, fill=color, width=max(2, int(r * 0.14)))
    d.arc((cx + r * 0.35, cy - r * 0.85, cx + r * 1.05, cy + r * 0.1), -90, 90, fill=color, width=max(2, int(r * 0.14)))
    d.rectangle((cx - r * 0.14, cy + r * 0.1, cx + r * 0.14, cy + r * 0.55), fill=color)
    d.rounded_rectangle((cx - r * 0.62, cy + r * 0.55, cx + r * 0.62, cy + r * 0.85), radius=int(r * 0.15), fill=color)


def vs_badge(d: ImageDraw.ImageDraw, center: tuple[float, float], r: float = 18) -> None:
    cx, cy = center
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CARD_HI, outline=LINE, width=2)
    text(d, (cx, cy + 1), "VS", int(r * 0.85), MUTED, True, anchor="mm")


def to_png_bytes(img: Image.Image, quality: int = 92) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
