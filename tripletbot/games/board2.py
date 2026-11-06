"""Light board games: Dots & Boxes, Nim, Memory Match, Snakes & Ladders."""
from __future__ import annotations

import math
from typing import Optional

from ..core.types import Control, InvalidAction, Option, Result, Select, ViewModel
from ..render import boards as B
from ..render import theme as T
from .base import Game


# ============================================================== DOTS & BOXES ⬛
class DotsBoxes(Game):
    key = "dots_boxes"
    name = "Dots & Boxes"
    tagline = "Close a box, keep the turn"
    emoji = "⬛"
    rules = "Join two dots per turn. Close the fourth side of a box to claim it and move again. Most boxes wins."
    N = 4

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        n = self.N
        self.h = [[None] * (n - 1) for _ in range(n)]
        self.v = [[None] * n for _ in range(n - 1)]
        self.boxes = [[None] * (n - 1) for _ in range(n - 1)]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last_edge: Optional[tuple] = None
        self._closed = 0

    def tally(self) -> list[int]:
        return [sum(row.count(i) for row in self.boxes) for i in range(len(self.players))]

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        t = self.tally()
        top = max(t)
        w = [i for i, v in enumerate(t) if v == top]
        if len(w) == 1:
            return Result(w[0], f"Boxes claimed: {t[0]} – {t[1]}.")
        return Result(None, f"Boxes split {t[0]} – {t[1]}.")

    def status(self) -> str:
        if self.done:
            t = self.tally()
            return f"Board closed · {t[0]}–{t[1]} boxes"
        t = self.tally()
        return f"{self.pname(self.turn_seat)} · {t[0]}–{t[1]} boxes"

    def prompt(self) -> str:
        return "Pick an edge to draw. Closing a box earns it and another turn." if not self.done else ""

    def _edges(self):
        out = []
        for r in range(self.N):
            for c in range(self.N - 1):
                if self.h[r][c] is None:
                    out.append((f"h{r}{c}", f"{chr(65 + r)}{c + 1} → {chr(65 + r)}{c + 2}", "➖"))
        for r in range(self.N - 1):
            for c in range(self.N):
                if self.v[r][c] is None:
                    out.append((f"v{r}{c}", f"{chr(65 + r)}{c + 1} → {chr(66 + r)}{c + 1}", "❕"))
        return out

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("The board is already closed.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        kind = action[0]
        try:
            r, c = int(action[1]), int(action[2])
        except (ValueError, IndexError):
            raise InvalidAction("Pick a valid edge.")
        if kind == "h":
            if not (0 <= r < self.N and 0 <= c < self.N - 1) or self.h[r][c] is not None:
                raise InvalidAction("That edge is not available.")
            self.h[r][c] = seat
        elif kind == "v":
            if not (0 <= r < self.N - 1 and 0 <= c < self.N) or self.v[r][c] is not None:
                raise InvalidAction("That edge is not available.")
            self.v[r][c] = seat
        else:
            raise InvalidAction("Unknown edge.")
        self.last_edge = (kind, r, c)

        closed = 0
        for br in range(self.N - 1):
            for bc in range(self.N - 1):
                if self.boxes[br][bc] is not None:
                    continue
                if self.h[br][bc] is not None and self.h[br + 1][bc] is not None and self.v[br][bc] is not None and self.v[br][bc + 1] is not None:
                    self.boxes[br][bc] = seat
                    closed += 1
        self._closed += closed
        if self._closed >= (self.N - 1) ** 2:
            self.done = True
            t = self.tally()
            top = max(t)
            w = [i for i, v in enumerate(t) if v == top]
            self.win_seat = w[0] if len(w) == 1 else None
        if closed:
            return f"{self.pname(seat)} closes {closed} box{'es' if closed > 1 else ''}!"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} draws a line"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [e[0] for e in self._edges()]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        acts = self.legal_actions(seat)
        if not acts:
            return None
        if self.rng.random() < {1: 0.6, 2: 0.3, 3: 0.1, 4: 0.0}.get(difficulty, 0.3):
            return self.rng.choice(acts)
        best, best_v = acts[0], -1e9
        for a in acts:
            child = self.clone()
            got = child.act(seat, a)
            mine = child.tally()[seat]
            theirs = child.tally()[self.other(seat)]
            v = (mine - theirs) * 10 + (1 if "closes" in got else 0)
            v += self.rng.random() * (3 if difficulty < 4 else 0.2)
            if v > best_v:
                best, best_v = a, v
        return best

    def view(self, seat: int) -> ViewModel:
        sels = []
        if not self.done and seat == self.turn_seat:
            opts = [Option(e[0], e[1], e[2]) for e in self._edges()]
            if opts:
                sels.append(Select("Pick a line to draw", opts[:25], row=0))
        return self._self_view(seat, selects=sels)

    def draw(self, f) -> None:
        n = self.N
        span = min(f.board[2] - f.board[0], f.board[3] - f.board[1]) - 40
        x0 = (f.board[0] + f.board[2]) / 2 - span / 2
        y0 = (f.board[1] + f.board[3]) / 2 - span / 2
        step = span / (n - 1)
        px = lambda c: x0 + c * step
        py = lambda r: y0 + r * step

        for br in range(n - 1):
            for bc in range(n - 1):
                owner = self.boxes[br][bc]
                box = (px(bc) + 4, py(br) + 4, px(bc + 1) - 4, py(br + 1) - 4)
                if owner is None:
                    f.d.rounded_rectangle(box, radius=10, fill=(24, 29, 41), outline=(34, 41, 57))
                else:
                    col = self.players[owner].color
                    f.d.rounded_rectangle(box, radius=10, fill=tuple(int(c * 0.22) for c in col), outline=col, width=2)
                    f.text(B.mid(box), self.players[owner].short(1).upper(), 26, col, bold=True, anchor="mm")

        for r in range(n):
            for c in range(n - 1):
                owner = self.h[r][c]
                p1, p2 = (px(c) + 8, py(r)), (px(c + 1) - 8, py(r))
                if owner is None:
                    f.d.line((p1, p2), fill=(52, 60, 80), width=5)
                else:
                    f.d.line((p1, p2), fill=self.players[owner].color, width=8)
                    f.d.ellipse((p1[0] - 3, p1[1] - 3, p1[0] + 3, p1[1] + 3), fill=(255, 255, 255))
        for r in range(n - 1):
            for c in range(n):
                owner = self.v[r][c]
                p1, p2 = (px(c), py(r) + 8), (px(c), py(r + 1) - 8)
                if owner is None:
                    f.d.line((p1, p2), fill=(52, 60, 80), width=5)
                else:
                    f.d.line((p1, p2), fill=self.players[owner].color, width=8)
        for r in range(n):
            for c in range(n):
                x, y = px(c), py(r)
                f.d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(206, 214, 228))
        for r in range(n):
            f.text((px(0) - 26, py(r)), chr(65 + r), 13, T.DIM, bold=True, anchor="mm")
        for c in range(n):
            f.text((px(c), py(0) - 24), str(c + 1), 13, T.DIM, bold=True, anchor="mm")


# ===================================================================== NIM 🧮
class Nim(Game):
    key = "nim"
    name = "Nim"
    tagline = "Take the last match to win"
    emoji = "🧮"
    rules = "Four heaps. On your turn remove 1–3 matches from a single heap. Whoever takes the final match wins."

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.heaps = [1, 3, 5, 7]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last: Optional[tuple[int, int]] = None

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, f"{self.pname(self.win_seat or 0)} took the last match.")

    def status(self) -> str:
        if self.done:
            return f"{self.pname(self.win_seat or 0)} wins the pile"
        return f"{self.pname(self.turn_seat)} to move · {sum(self.heaps)} matches left"

    def prompt(self) -> str:
        return "Remove 1, 2 or 3 matches from one heap."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Game over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if not action.startswith("h") or "t" not in action:
            raise InvalidAction("Invalid move.")
        try:
            i = int(action[1:action.index("t")])
            k = int(action[action.index("t") + 1:])
        except ValueError:
            raise InvalidAction("Invalid move.")
        if not 0 <= i < len(self.heaps):
            raise InvalidAction("No such heap.")
        if not 1 <= k <= min(3, self.heaps[i]):
            raise InvalidAction("You cannot take that many.")
        self.heaps[i] -= k
        self.last = (i, k)
        if sum(self.heaps) == 0:
            self.done, self.win_seat = True, seat
            return f"{self.pname(seat)} takes the last match!"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} takes {k} from heap {i + 1}"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [f"h{i}t{k}" for i, h in enumerate(self.heaps) for k in range(1, min(3, h) + 1)]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        acts = self.legal_actions(seat)
        if not acts:
            return None
        if difficulty <= 1 and self.rng.random() < 0.5:
            return self.rng.choice(acts)
        for i, h in enumerate(self.heaps):
            if h % 4:
                take = h % 4
                if 1 <= take <= 3 and f"h{i}t{take}" in acts:
                    return f"h{i}t{take}"
        return self.rng.choice(acts)

    def view(self, seat: int) -> ViewModel:
        btns = []
        for i, h in enumerate(self.heaps):
            for k in range(1, 4):
                btns.append(Control(f"h{i}t{k}", f"{i + 1} −{k}", "", "primary" if k <= h else "secondary", i, k > h))
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        rows = len(self.heaps)
        top = y0 + 16
        avail = (y1 - y0) - 40
        row_h = avail / rows
        for i, h in enumerate(self.heaps):
            cy = top + i * row_h + row_h / 2
            box = (x0 + 10, cy - row_h / 2 + 6, x1 - 10, cy + row_h / 2 - 6)
            f.d.rounded_rectangle(box, radius=14, fill=(26, 31, 44), outline=(38, 46, 62), width=2)
            f.text((box[0] + 18, cy), f"HEAP {i + 1}", 15, T.DIM, bold=True, anchor="lm")
            start_x = box[0] + 130
            spacing = 26
            for m in range(7):
                mx = start_x + m * spacing
                if m < h:
                    col = self.players[self.turn_seat].color if not self.done else T.GOLD
                    f.d.rounded_rectangle((mx, cy - 18, mx + 9, cy + 18), radius=4, fill=(226, 214, 188))
                    f.d.ellipse((mx - 1, cy - 26, mx + 10, cy - 12), fill=col)
                else:
                    f.d.rounded_rectangle((mx, cy - 18, mx + 9, cy + 18), radius=4, outline=(44, 52, 70), width=1)
            f.text((box[2] - 18, cy), str(h), 26, T.TEXT, bold=True, anchor="rm")


# ============================================================ MEMORY MATCH 🃏
SYMBOLS = [
    ("circle", (52, 211, 153)),
    ("square", (96, 165, 250)),
    ("triangle", (255, 199, 84)),
    ("star", (244, 114, 182)),
    ("diamond", (167, 139, 250)),
    ("ring", (34, 211, 238)),
    ("cross", (248, 113, 113)),
    ("hex", (251, 146, 60)),
]


def draw_symbol(d, center, r, kind, color):
    cx, cy = center
    if kind == "circle":
        T.disc(d, center, r, color)
    elif kind == "square":
        d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=int(r * 0.3), fill=color)
    elif kind == "triangle":
        d.polygon([(cx, cy - r), (cx + r, cy + r * 0.8), (cx - r, cy + r * 0.8)], fill=color)
    elif kind == "star":
        T.star(d, center, r, color)
    elif kind == "diamond":
        T.diamond(d, center, r, color)
    elif kind == "ring":
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=max(4, int(r * 0.32)))
    elif kind == "cross":
        T.cross(d, center, r * 0.85, color, width=max(4, int(r * 0.34)))
    else:
        pts = [(cx + r * math.cos(math.pi / 3 * i - math.pi / 6), cy + r * math.sin(math.pi / 3 * i - math.pi / 6)) for i in range(6)]
        d.polygon(pts, fill=color)


class Memory(Game):
    key = "memory"
    name = "Memory Match"
    tagline = "Flip two, remember everything"
    emoji = "🃏"
    rules = "Flip two cards per turn. A matching pair scores and lets you go again. Most pairs wins."
    ROWS, COLS = 4, 4

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        ids = [i % 8 for i in range(self.ROWS * self.COLS)]
        self.rng.shuffle(ids)
        self.layout = ids
        self.flipped: list[int] = []
        self.matched: set[int] = set()
        self.pairs = [0 for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last_match: Optional[tuple[int, int]] = None
        self.seen: dict[int, dict[int, int]] = {p.index: {} for p in self.players}

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        top = max(self.pairs)
        w = [i for i, v in enumerate(self.pairs) if v == top]
        if len(w) == 1:
            return Result(w[0], f"Pairs found: {' – '.join(str(v) for v in self.pairs)}")
        return Result(None, "Dead heat on pairs.")

    def status(self) -> str:
        if self.done:
            return "All pairs found"
        return f"{self.pname(self.turn_seat)} · {self.pairs[self.turn_seat]} pairs"

    def prompt(self) -> str:
        if self.done:
            return ""
        return "Now pick a matching card." if self.flipped else "Flip a card to start your turn."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Game over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if not action.startswith("c") or not action[1:].isdigit():
            raise InvalidAction("Pick a card.")
        if len(self.flipped) >= 2:
            self.flipped.clear()
        i = int(action[1:])
        if not 0 <= i < len(self.layout):
            raise InvalidAction("No such card.")
        if i in self.matched or i in self.flipped:
            raise InvalidAction("That card is already face up.")

        self.flipped.append(i)
        for p in self.players:
            self.seen.setdefault(p.index, {})[i] = self.layout[i]

        if len(self.flipped) < 2:
            return f"{self.pname(seat)} flips a card"

        a, b = self.flipped
        if self.layout[a] == self.layout[b]:
            self.matched.update((a, b))
            self.pairs[seat] += 1
            self.flipped.clear()
            self.last_match = (a, b)
            if len(self.matched) == len(self.layout):
                self.done = True
                top = max(self.pairs)
                w = [k for k, v in enumerate(self.pairs) if v == top]
                self.win_seat = w[0] if len(w) == 1 else None
            return f"{self.pname(seat)} matches a pair!"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} misses"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [f"c{i}" for i in range(len(self.layout)) if i not in self.matched and i not in self.flipped]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        acts = [int(a[1:]) for a in self.legal_actions(seat)]
        if not acts:
            return None
        mem = self.seen.setdefault(seat, {})
        recall = {1: 0.35, 2: 0.7, 3: 0.95, 4: 1.0}.get(difficulty, 0.7)
        known = {i: s for i, s in mem.items() if i not in self.matched and i not in self.flipped}
        if self.flipped:
            target_sym = self.layout[self.flipped[0]]
            for i, s in known.items():
                if s == target_sym and self.rng.random() < recall:
                    return f"c{i}"
        by_sym: dict[int, list[int]] = {}
        for i, s in known.items():
            by_sym.setdefault(s, []).append(i)
        for s, idxs in by_sym.items():
            if len(idxs) >= 2 and self.rng.random() < recall:
                return f"c{self.rng.choice(idxs)}"
        unknown = [i for i in acts if i not in known]
        return f"c{self.rng.choice(unknown or acts)}"

    def view(self, seat: int) -> ViewModel:
        btns = [Control(f"c{i}", str(i + 1), "", "secondary", i // self.COLS) for i in range(len(self.layout))]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=12)
        rects = B.grid(bsq, self.COLS, self.ROWS, gap=10)
        for i, r in enumerate(rects):
            sym = self.layout[i]
            kind, color = SYMBOLS[sym]
            cx, cy = B.mid(r)
            rad = (r[2] - r[0]) / 2
            face_up = i in self.matched or i in self.flipped
            if face_up:
                fill = tuple(int(c * 0.24) for c in color)
                if i in self.matched:
                    fill = (24, 28, 39)
                f.d.rounded_rectangle(r, radius=12, fill=fill, outline=color, width=3 if i in self.flipped else 2)
                draw_symbol(f.d, (cx, cy), rad * 0.45, kind, color if i not in self.matched else tuple(int(c * 0.6) for c in color))
                if i in self.matched:
                    T.check(f.d, (r[2] - 20, r[1] + 18), 8, (52, 211, 153), 3)
            else:
                f.d.rounded_rectangle(r, radius=12, fill=(32, 38, 54), outline=(46, 55, 76), width=2)
                f.d.rounded_rectangle((r[0] + 7, r[1] + 7, r[2] - 7, r[3] - 7), radius=8, outline=(40, 48, 66), width=1)
                T.diamond(f.d, (cx, cy), rad * 0.24, (48, 57, 78))
                f.text((r[0] + 16, r[1] + 10), str(i + 1), 12, (54, 63, 84), bold=True)


# ======================================================== SNAKES & LADDERS 🐍
class SnakesLadders(Game):
    key = "snakes"
    name = "Snakes & Ladders"
    tagline = "Roll, climb, slide"
    emoji = "🐍"
    rules = "Roll the dice to race to square 100. Ladders lift you, snakes drag you down. Exact 100 needed."

    LADDERS = {3: 22, 8: 26, 20: 41, 28: 51, 36: 57, 47: 66, 62: 79, 71: 90, 88: 97}
    SNAKES = {17: 6, 34: 12, 48: 26, 54: 38, 64: 60, 76: 44, 87: 24, 93: 73, 99: 78}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.pos = [0 for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last_roll: Optional[int] = None
        self.rolls = 0

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, f"{self.pname(self.win_seat or 0)} reached 100 in {self.rolls} rolls.")

    def status(self) -> str:
        if self.done:
            return f"{self.pname(self.win_seat or 0)} wins the race"
        return f"{self.pname(self.turn_seat)} to roll · at {self.pos[self.turn_seat]}"

    def prompt(self) -> str:
        return "Hit Roll to throw the dice."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Race over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if action != "roll":
            raise InvalidAction("Only the dice can move you.")
        d = self.rng.randint(1, 6)
        self.last_roll = d
        self.rolls += 1
        new = self.pos[seat] + d
        note = ""
        if new > 100:
            new = self.pos[seat]
            note = " (needs exact 100)"
        if new in self.LADDERS:
            new = self.LADDERS[new]
            note += " 🪜 ladder!"
        elif new in self.SNAKES:
            new = self.SNAKES[new]
            note += " 🐍 snake!"
        self.pos[seat] = new
        if new == 100:
            self.done, self.win_seat = True, seat
            return f"{self.pname(seat)} rolls {d} and hits 100!"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} rolls {d} → {new}{note}"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return ["roll"]

    def view(self, seat: int) -> ViewModel:
        return self._self_view(seat, [Control("roll", "Roll dice", "🎲", "primary", 0)])

    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=10)
        n = 10
        rects = B.grid(bsq, n, n, gap=2)
        cell_of = {}
        for num in range(1, 101):
            idx = num - 1
            row = n - 1 - (idx // n)
            col = idx % n if row % 2 == (n - 1) % 2 else n - 1 - (idx % n)
            # boustrophedon: even rows (from bottom) left->right
            row_from_bottom = idx // n
            col = idx % n if row_from_bottom % 2 == 0 else n - 1 - (idx % n)
            rr = n - 1 - row_from_bottom
            r = rects[rr * n + col]
            cell_of[num] = r
            light = (rr + col) % 2 == 0
            f.d.rectangle(r, fill=(44, 53, 72) if light else (33, 40, 55))
            f.text((r[0] + 5, r[1] + 3), str(num), 12, (156, 170, 196), bold=True)
        for src, dst in self.LADDERS.items():
            a, b = B.mid(cell_of[src]), B.mid(cell_of[dst])
            f.d.line((a, b), fill=(120, 160, 210), width=3)
            f.d.line((a[0] + 4, a[1], b[0] + 4, b[1]), fill=(120, 160, 210), width=3)
            steps = 6
            for s in range(1, steps):
                t = s / steps
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                f.d.line((p[0] - 2, p[1], p[0] + 6, p[1]), fill=(140, 186, 240), width=2)
        for src, dst in self.SNAKES.items():
            a, b = B.mid(cell_of[src]), B.mid(cell_of[dst])
            pts = []
            for s in range(21):
                t = s / 20
                x = a[0] + (b[0] - a[0]) * t + math.sin(t * math.pi * 3) * 12
                y = a[1] + (b[1] - a[1]) * t + math.cos(t * math.pi * 3) * 8
                pts.append((x, y))
            f.d.line(pts, fill=(220, 100, 120), width=4, joint="curve")
            f.d.ellipse((b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6), fill=(240, 130, 150))
        for i, p in enumerate(self.players):
            if self.pos[i] <= 0:
                continue
            r = cell_of[self.pos[i]]
            cx, cy = B.mid(r)
            off = 7 * (i - 0.5)
            T.disc(f.d, (cx + off, cy + off), 11, p.color)
            f.d.ellipse((cx + off - 11, cy + off - 11, cx + off + 11, cy + off + 11), outline=(12, 16, 24), width=2)
        if self.last_roll:
            f.d.rounded_rectangle((f.board[2] - 116, f.board[1] + 4, f.board[2] - 8, f.board[1] + 40), radius=10, fill=(38, 45, 62))
            f.text((f.board[2] - 62, f.board[1] + 22), f"LAST ROLL {self.last_roll}", 12, T.GOLD, bold=True, anchor="mm")
