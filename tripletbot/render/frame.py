"""The frame every match is rendered into: header, board card, lineup, live log, status."""
from __future__ import annotations

from typing import Optional

from PIL import Image, ImageDraw

from ..core.types import LogEntry, MatchMeta, Player, Result
from . import theme as T


class Frame:
    """Mutable drawing surface handed to each game's ``draw()`` method."""

    def __init__(
        self,
        meta: MatchMeta,
        players: list[Player],
        scores: list[float],
        log: Optional[list[LogEntry]] = None,
        accent: tuple = T.ACCENT,
        show_result: bool = True,
    ):
        self.meta = meta
        self.players = players
        self.scores = scores
        self.log = log or []
        self.accent = accent
        self.show_result = show_result
        self.img = T.background().copy()
        self.d = ImageDraw.Draw(self.img)
        self.board = (48, 150, 756, 672)          # drawing area for the game
        self.sidebar = (792, 128, 1072, 692)

    # ---------------------------------------------------------------- wrappers
    def text(self, xy, s, size=20, color=T.TEXT, bold=False, anchor="la", mono=False, stroke=0, stroke_fill=None):
        return T.text(self.d, xy, s, size, color, bold, anchor, mono, stroke, stroke_fill)

    def measure(self, s, size, bold=False, mono=False):
        return T.measure(s, size, bold, mono)

    def wrap(self, s, size, max_w, bold=False, max_lines=99):
        return T.wrap(s, size, max_w, bold, max_lines)

    def ellipsize(self, s, size, max_w, bold=False):
        return T.ellipsize(s, size, max_w, bold)

    def block(self, xy, s, size=18, color=T.MUTED, bold=False, max_w=200, leading=1.35, max_lines=99):
        return T.block(self.d, xy, s, size, color, bold, max_w, leading, max_lines)

    def card(self, box, radius=18, fill=T.CARD, outline=T.LINE_SOFT, width=2, shadow=14):
        T.card(self.img, self.d, box, radius, fill, outline, width, shadow)

    def inset(self, box, radius=14, fill=T.CARD_LO, outline=T.LINE_SOFT, width=1):
        T.inset(self.d, box, radius, fill, outline, width)

    def pill(self, xy, s, size=16, fg=T.TEXT, bg=T.CARD_HI, bold=True, outline=None, anchor_right=False, icon=""):
        return T.pill(self.img, self.d, xy, s, size, fg, bg, bold, outline=outline, anchor_right=anchor_right, icon=icon)

    # ------------------------------------------------------------- composition
    def render(self, game) -> Image.Image:
        self._header()
        T.card(self.img, self.d, (28, 128, 776, 692), radius=22, fill=T.CARD)
        self.d.rounded_rectangle(self.board, radius=16, fill=(20, 24, 34))
        game.draw(self)
        self._sidebar(game)
        self._footer()
        if game.is_over() and self.show_result:
            self._result_overlay(game)
        return self.img

    # -------------------------------------------------------------------- parts
    def _header(self) -> None:
        T.logo(self.img, self.d, (34, 24, 94, 84))
        self.text((112, 26), self.meta.game_name, 33, T.TEXT, bold=True)
        self.text((114, 66), self.meta.tagline.upper(), 15, T.DIM, bold=True)
        # right side pills
        x = 1066
        box = self.pill((x, 34), self.meta.mode, 15, fg=self.accent, bg=(30, 33, 48), outline=self.accent, anchor_right=True)
        self.pill((box[0] - 10, 34), f"ROUND {self.meta.round_no}/{self.meta.rounds}", 15, fg=T.TEXT, bg=(30, 33, 48), anchor_right=True)
        T.divider(self.d, 28, 112, 1072)

    def _footer(self) -> None:
        T.divider(self.d, 28, 698, 1072, (30, 36, 50))
        self.text((30, 704), "TripleTBot Arcade", 13, (72, 82, 104), bold=True)
        right = f"MATCH {self.meta.code}" if self.meta.code else "TRIPLETBOT"
        self.text((1072, 704), right, 13, (72, 82, 104), bold=True, anchor="ra")

    def _sidebar(self, game) -> None:
        x0, y0, x1, y1 = self.sidebar
        T.card(self.img, self.d, self.sidebar, radius=22, fill=T.CARD)
        pad = 16
        inner_w = x1 - x0 - pad * 2
        y = y0 + 16
        self.text((x0 + pad, y), "LINEUP", 13, T.DIM, bold=True)
        self.text((x1 - pad, y), f"{len(self.players)} SEATS", 13, T.DIM, bold=True, anchor="ra")
        y += 26

        acting = set(game.acting())
        n = len(self.players)
        card_h = 74 if n <= 2 else (66 if n == 3 else 60)
        for p in self.players:
            self._player_card(p, x0 + pad, y, inner_w, card_h, p.index in acting)
            y += card_h + 7

        y += 8
        T.divider(self.d, x0 + pad, y, x1 - pad)
        y += 12
        self.text((x0 + pad, y), "LIVE LOG", 13, T.DIM, bold=True)
        y += 24

        strip_h = 108
        log_bottom = y1 - pad - strip_h - 12
        line_h = 22
        slots = max(1, int((log_bottom - y) // line_h))
        entries = self.log[-slots:]
        for e in entries:
            color = e.color if e.color else T.MUTED
            self.d.ellipse((x0 + pad + 2, y + 7, x0 + pad + 8, y + 13), fill=color)
            label = self.ellipsize(e.text, 14, inner_w - 22)
            self.text((x0 + pad + 16, y + 1), label, 14, T.MUTED)
            y += line_h

        # status strip
        sy = y1 - pad - strip_h
        T.inset(self.d, (x0 + pad, sy, x1 - pad, sy + strip_h), radius=14, fill=(26, 24, 44), outline=(52, 46, 84))
        self.d.rounded_rectangle((x0 + pad, sy + 12, x0 + pad + 3, sy + strip_h - 12), radius=2, fill=self.accent)
        status = game.status()
        ty = sy + 12
        for line in self.wrap(status, 17, inner_w - 26, bold=True, max_lines=2):
            self.text((x0 + pad + 14, ty), line, 17, T.TEXT, bold=True)
            ty += 21
        prompt = getattr(self, "prompt", "") or ""
        if prompt:
            for line in self.wrap(prompt, 13, inner_w - 26, max_lines=2):
                self.text((x0 + pad + 14, ty + 2), line, 13, T.MUTED)
                ty += 16

    def _player_card(self, p: Player, x, y, w, h, is_turn: bool) -> None:
        box = (x, y, x + w, y + h)
        fill = T.CARD_HI if is_turn else T.CARD_LO
        outline = p.color if is_turn else T.LINE_SOFT
        T.inset(self.d, box, radius=14, fill=fill, outline=outline, width=2 if is_turn else 1)
        if is_turn:
            T.glow_box(self.img, self.d, box, tuple(c // 3 for c in p.color), radius=14, width=2, blur=8)

        r = 20 if h >= 70 else 17
        cx = x + 16 + r
        cy = y + h / 2
        T.avatar(self.img, self.d, (cx, cy), r, p.name, p.color, p.avatar_bytes, ring=2, dim=not is_turn)

        tx = cx + r + 12
        name_w = w - (tx - x) - 62
        self.text((tx, y + (13 if h >= 70 else 10)), self.ellipsize(p.name, 17, name_w, bold=True), 17, T.TEXT, bold=True)
        sub = p.sub
        self.text((tx, y + (35 if h >= 70 else 30)), sub, 11, p.color if is_turn else T.DIM, bold=True)
        if is_turn:
            self.text((tx, y + h - 20), "YOUR MOVE", 11, p.color, bold=True)

        score = self.scores[p.index] if p.index < len(self.scores) else 0
        s = f"{score:g}"
        self.text((x + w - 16, y + h / 2 - 4), s, 27, T.TEXT, bold=True, anchor="rm")
        self.text((x + w - 16, y + h / 2 + 20), "WINS", 9, T.DIM, bold=True, anchor="rm")

    def _result_overlay(self, game) -> None:
        result: Result = getattr(game, "final_result", None) or game.result()  # type: ignore[assignment]
        if result is None:
            return
        bx0, by0, bx1, by1 = self.board
        layer = Image.new("RGBA", (T.W, T.H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle((bx0, by0, bx1, by1), radius=16, fill=(8, 10, 16, 205))
        box = (bx0 + 60, by0 + 68, bx1 - 60, by1 - 68)
        ld.rounded_rectangle(box, radius=20, fill=(23, 27, 38, 250), outline=(*self.accent, 255), width=2)
        self.img = Image.alpha_composite(self.img.convert("RGBA"), layer).convert("RGB")
        self.d = ImageDraw.Draw(self.img)

        cx = (box[0] + box[2]) / 2
        if result.winner is None:
            T.star(self.d, (cx, box[1] + 62), 26, T.GOLD)
            self.text((cx, box[1] + 104), "DRAW", 40, T.TEXT, bold=True, anchor="ma")
        else:
            p = self.players[result.winner]
            T.trophy(self.d, (cx, box[1] + 58), 30)
            self.text((cx, box[1] + 104), "WINNER", 15, T.GOLD, bold=True, anchor="ma")
            self.text((cx, box[1] + 128), self.ellipsize(p.name, 40, box[2] - box[0] - 80, True), 36, T.TEXT, bold=True, anchor="ma")
            T.avatar(self.img, self.d, (cx, box[1] + 196), 26, p.name, p.color, p.avatar_bytes, ring=3)

        y = box[1] + 236 if result.winner is not None else box[1] + 150
        for line in self.wrap(result.reason, 17, box[2] - box[0] - 80, max_lines=2):
            self.text((cx, y), line, 17, T.MUTED, anchor="ma")
            y += 22
        y += 10
        scoreline = "  ·  ".join(f"{p.short(12)} {self.scores[p.index]:g}" for p in self.players)
        self.text((cx, y), scoreline, 16, T.TEXT, bold=True, anchor="ma")
