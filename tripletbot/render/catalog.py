"""The /games poster: every title in the arcade on one card."""
from __future__ import annotations

from ..games import CATALOG
from . import theme as T


def catalog_poster() -> "T.Image.Image":
    img = T.background().copy()
    d = T.ImageDraw.Draw(img)
    T.logo(img, d, (34, 26, 96, 88))
    T.text(d, (112, 28), "TripleTBot Arcade", 34, T.TEXT, bold=True)
    T.text(d, (114, 70), f"{len(CATALOG)} GAMES · BUTTONS, NOT ASCII", 15, T.DIM, bold=True)
    T.pill(img, d, (1066, 38), "LIVE BOARDS", 15, fg=T.ACCENT, bg=(30, 33, 48), outline=T.ACCENT, anchor_right=True)
    T.divider(d, 28, 112, 1072)

    cols, rows = 4, 6
    pad_x, top = 28, 124
    gap_x, gap_y = 12, 8
    cw = (T.W - pad_x * 2 - gap_x * (cols - 1)) / cols
    ch = (T.H - top - 46 - gap_y * (rows - 1)) / rows
    for i, cls in enumerate(CATALOG[: cols * rows]):
        r, c = divmod(i, cols)
        x = pad_x + c * (cw + gap_x)
        y = top + r * (ch + gap_y)
        box = (x, y, x + cw, y + ch)
        accent = T.SEAT_COLORS[i % len(T.SEAT_COLORS)]
        d.rounded_rectangle(box, radius=14, fill=(25, 30, 42), outline=(40, 48, 66), width=1)
        d.rounded_rectangle((x, y + 10, x + 4, y + ch - 10), radius=2, fill=accent)
        T.text(d, (x + 16, y + 10), f"{i + 1:02d}", 13, accent, bold=True)
        T.text(d, (x + 40, y + 8), T.ellipsize(cls.name, 16, cw - 56, True), 16, T.TEXT, bold=True)
        T.block(d, (x + 16, y + 30), cls.tagline, 12, T.MUTED, max_w=cw - 28, max_lines=1)
        T.text(d, (x + 16, y + ch - 20), f"/{cls.key}", 12, accent, bold=True, mono=True)
        seats = "1v1" if cls.max_players <= 2 else f"2-{cls.max_players}"
        T.text(d, (x + cw - 14, y + ch - 20), seats, 11, T.DIM, bold=True, anchor="ra")
    T.text(d, (30, T.H - 28), "Every match renders a fresh frame — spectators see every move live.", 13, (78, 88, 110), bold=True)
    T.text(d, (1072, T.H - 28), "/play · /rules · /stats", 13, (78, 88, 110), bold=True, anchor="ra")
    return img
