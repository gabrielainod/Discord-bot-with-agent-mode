"""Puzzle/duel games on grids: Minesweeper Duel, 2048 Race, Battleship."""
from __future__ import annotations

import random
from typing import Optional

from ..core.types import Control, InvalidAction, Result, ViewModel
from ..render import boards as B
from ..render import theme as T
from .base import Game


def _seed(rng: random.Random, n: int) -> list[int]:
    return [rng.random() for _ in range(n)]


# ========================================================= MINESWEEPER DUEL 💣
class Minesweeper(Game):
    key = "minesweeper"
    name = "Minesweeper Duel"
    tagline = "Shared field, sharp nerves"
    emoji = "💣"
    rules = "Reveal a tile: safe ground scores you a point, a mine costs two. The field is shared, the nerves are yours."

    N = 6
    MINES = 6

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        cells = [(r, c) for r in range(self.N) for c in range(self.N)]
        self.rng.shuffle(cells)
        self.mines = set(cells[: self.MINES])
        self.revealed: set[tuple[int, int]] = set()
        self.flagged: set[tuple[int, int]] = set()
        self.points = [0 for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last: Optional[tuple[int, int]] = None
        self.last_boom = False
        self.safe_total = self.N * self.N - self.MINES

    def _count(self, r: int, c: int) -> int:
        return sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0) and (r + dr, c + dc) in self.mines)

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        top = max(self.points)
        w = [i for i, v in enumerate(self.points) if v == top]
        if len(w) == 1:
            return Result(w[0], f"Field cleared · {self.points[0]} – {self.points[1]} points.")
        return Result(None, f"Field cleared on level points ({self.points[0]} – {self.points[1]}).")

    def status(self) -> str:
        if self.done:
            return "Field cleared"
        return f"{self.pname(self.turn_seat)} · {self.points[0]}–{self.points[1]} pts"

    def prompt(self) -> str:
        return "Pick a row, then a column to dig."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Field cleared.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        rc = self.coord_handle(seat, action)
        if rc is None:
            return ""
        r, c = rc
        if not (0 <= r < self.N and 0 <= c < self.N):
            raise InvalidAction("Out of bounds.")
        if (r, c) in self.revealed:
            raise InvalidAction("Already revealed.")
        self.revealed.add((r, c))
        self.last = (r, c)
        if (r, c) in self.mines:
            self.points[seat] = max(-5, self.points[seat] - 2)
            self.last_boom = True
            msg = f"{self.pname(seat)} hits a mine (−2)"
        else:
            self.points[seat] += 1
            self.last_boom = False
            msg = f"{self.pname(seat)} finds safe ground (+1)"
        safe_found = len([x for x in self.revealed if x not in self.mines])
        if safe_found >= self.safe_total:
            self.done = True
            top = max(self.points)
            w = [i for i, v in enumerate(self.points) if v == top]
            self.win_seat = w[0] if len(w) == 1 else None
            return msg + " — field cleared"
        self.turn_seat = self.other(seat)
        return msg

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        out = []
        for r in range(self.N):
            for c in range(self.N):
                if (r, c) not in self.revealed:
                    out.append(f"r:{r}")
                    out.append(f"c:{c}")
        return out

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        # engine policy: prefer tiles far from revealed mines, otherwise dig blind
        candidates = [(r, c) for r in range(self.N) for c in range(self.N) if (r, c) not in self.revealed]
        if not candidates:
            return None
        safe = []
        for r, c in candidates:
            near_mine = False
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    cell = (r + dr, c + dc)
                    if cell in self.revealed and cell in self.mines:
                        near_mine = True
            if not near_mine:
                safe.append((r, c))
        pool = safe or candidates
        r, c = (self.rng.choice(pool) if difficulty <= 2 or not safe else safe[0])
        self.pending.setdefault(seat, {})["r"] = r
        return f"c:{c}"

    def view(self, seat: int) -> ViewModel:
        sels = self.coord_selects(
            seat, self.N, self.N,
            row_labels=lambda i: f"Row {i + 1}",
            col_labels=lambda i: f"Column {i + 1}",
            row_placeholder="Row (1–6)",
            col_placeholder="Column (1–6)",
        )
        return self._self_view(seat, selects=sels)

    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=14)
        rects = B.grid(bsq, self.N, self.N, gap=7)
        for i, r in enumerate(rects):
            rr, cc = divmod(i, self.N)
            cell = (rr, cc)
            cx, cy = B.mid(r)
            if cell not in self.revealed:
                f.d.rounded_rectangle(r, radius=8, fill=(46, 56, 78), outline=(60, 72, 98), width=2)
                f.d.rounded_rectangle((r[0] + 3, r[1] + 3, r[2] - 3, r[1] + 9), radius=4, fill=(62, 76, 104))
            else:
                boom = cell in self.mines
                f.d.rounded_rectangle(r, radius=8, fill=(78, 40, 48) if boom else (28, 34, 48), outline=(120, 62, 72) if boom else (44, 53, 72), width=2)
                if boom:
                    T.star(f.d, (cx, cy), (r[2] - r[0]) * 0.28, (248, 113, 113), points=8)
                    f.d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(40, 20, 24))
                else:
                    n = self._count(rr, cc)
                    colors = {1: (96, 165, 250), 2: (52, 211, 153), 3: (255, 199, 84), 4: (251, 146, 60), 5: (248, 113, 113), 6: (244, 114, 182)}
                    if n:
                        f.text((cx, cy + 1), str(n), 26, colors.get(n, T.TEXT), bold=True, anchor="mm")
        # score chips
        x = f.board[0]
        y = f.board[1] + 18
        for i, p in enumerate(self.players):
            label = f"{p.short(10)}  {self.points[i]:+d}"
            w = T.measure(label, 14, True)[0] + 24
            f.d.rounded_rectangle((x, y - 20, x + w, y + 4), radius=12, fill=T.CARD_LO, outline=p.color if i == self.turn_seat and not self.done else T.LINE_SOFT)
            f.text((x + 12, y - 8), label, 14, T.TEXT if i == self.turn_seat else T.MUTED, bold=True, anchor="lm")
            x += w + 10


# ================================================================ 2048 RACE 🔢
TILE_COLORS = {
    0: (30, 36, 50), 2: (58, 68, 92), 4: (72, 84, 112), 8: (249, 148, 82), 16: (248, 126, 62),
    32: (246, 104, 70), 64: (238, 78, 62), 128: (255, 199, 84), 256: (252, 186, 60),
    512: (247, 172, 40), 1024: (124, 92, 255), 2048: (34, 211, 238),
}


class Game2048(Game):
    key = "game2048"
    name = "2048 Race"
    tagline = "Two boards, one race to 2048"
    emoji = "🔢"
    rules = "Slide your tiles with the arrows. Equal tiles merge. First to build a 2048 tile wins — most points breaks a stalemate."
    simultaneous = True
    MAX_MOVES = 160

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.boards = [self._fresh(), self._fresh()]
        self.points = [0 for _ in self.players]
        self.moves = [0 for _ in self.players]
        self.total = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""
        self.best = [2, 2]

    def _fresh(self) -> list[list[int]]:
        b = [[0] * 4 for _ in range(4)]
        self._spawn(b)
        self._spawn(b)
        return b

    def _spawn(self, b) -> None:
        empties = [(r, c) for r in range(4) for c in range(4) if b[r][c] == 0]
        if not empties:
            return
        r, c = self.rng.choice(empties)
        b[r][c] = 4 if self.rng.random() < 0.12 else 2

    def is_over(self) -> bool:
        if not self.done and self.total >= self.MAX_MOVES:
            self._finish("Move limit reached.")
        return self.done

    def _finish(self, reason: str) -> None:
        self.done = True
        self.reason = reason
        best = [self.best[0], self.best[1]]
        top = max(best)
        w = [i for i, v in enumerate(best) if v == top]
        self.win_seat = w[0] if len(w) == 1 else None

    @staticmethod
    def _slide(row: list[int]) -> tuple[list[int], int]:
        vals = [v for v in row if v]
        out: list[int] = []
        gained = 0
        i = 0
        while i < len(vals):
            if i + 1 < len(vals) and vals[i] == vals[i + 1]:
                out.append(vals[i] * 2)
                gained += vals[i] * 2
                i += 2
            else:
                out.append(vals[i])
                i += 1
        out += [0] * (4 - len(out))
        return out, gained

    def _move(self, board, direction: str):
        b = [row[:] for row in board]
        gained = 0
        if direction in ("left", "right"):
            for r in range(4):
                row = b[r] if direction == "left" else b[r][::-1]
                new, g = self._slide(row)
                gained += g
                b[r] = new if direction == "left" else new[::-1]
        else:
            for c in range(4):
                col = [b[r][c] for r in range(4)]
                if direction == "down":
                    col = col[::-1]
                new, g = self._slide(col)
                gained += g
                if direction == "down":
                    new = new[::-1]
                for r in range(4):
                    b[r][c] = new[r]
        return b, gained

    def _can_move(self, board) -> bool:
        for d in ("left", "right", "up", "down"):
            nb, _ = self._move(board, d)
            if nb != board:
                return True
        return False

    def acting(self) -> list[int]:
        if self.is_over():
            return []
        return [p.index for p in self.players]

    def turn(self) -> int:
        return -1

    def result(self) -> Optional[Result]:
        if not self.is_over():
            return None
        return Result(self.win_seat, f"{self.reason} Best tiles {' / '.join(str(b) for b in self.best)}.")

    def status(self) -> str:
        if self.done:
            return "Race finished"
        return f"Race to 2048 · {self.points[0]} vs {self.points[1]}"

    def prompt(self) -> str:
        return "Tap an arrow to slide your own board."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Race finished.")
        if action not in ("left", "right", "up", "down"):
            raise InvalidAction("Use an arrow.")
        board = self.boards[seat]
        nb, gained = self._move(board, action)
        if nb == board:
            raise InvalidAction("That move changes nothing.")
        self.boards[seat] = nb
        self.points[seat] += gained
        self.moves[seat] += 1
        self.total += 1
        self._spawn(nb)
        mx = max(max(row) for row in nb)
        if mx > self.best[seat]:
            self.best[seat] = mx
        if mx >= 2048:
            self.done = True
            self.win_seat = seat
            self.reason = f"{self.pname(seat)} built 2048!"
            return f"{self.pname(seat)} builds 2048!"
        stuck = [i for i in range(len(self.players)) if not self._can_move(self.boards[i])]
        if len(stuck) == len(self.players):
            self._finish("Everyone jammed.")
        return f"{self.pname(seat)} slides {action} (+{gained})"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done:
            return []
        out = []
        for d in ("left", "right", "up", "down"):
            nb, _ = self._move(self.boards[seat], d)
            if nb != self.boards[seat]:
                out.append(d)
        return out

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        acts = self.legal_actions(seat)
        if not acts:
            return None
        if difficulty <= 1:
            return self.rng.choice(acts)
        best, best_v = acts[0], -1e9
        for d in acts:
            nb, gained = self._move(self.boards[seat], d)
            empties = sum(1 for r in range(4) for c in range(4) if nb[r][c] == 0)
            v = gained * 2 + empties * 12 + max(max(row) for row in nb)
            v += self.rng.random() * (14 - 2 * difficulty)
            if v > best_v:
                best, best_v = d, v
        return best

    def view(self, seat: int) -> ViewModel:
        btns = [
            Control("up", "Up", "⬆️", "primary", 0),
            Control("down", "Down", "⬇️", "primary", 0),
            Control("left", "Left", "⬅️", "primary", 0),
            Control("right", "Right", "➡️", "primary", 0),
        ]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        gap = 26
        w = (708 - gap) / 2
        top = f.board[1] + max(10, (522 - w) / 2 - 14)
        for i in range(len(self.players)):
            left = f.board[0] + i * (w + gap)
            box = (left, top, left + w, top + w)
            p = self.players[i]
            f.d.rounded_rectangle(box, radius=16, fill=(22, 27, 38), outline=p.color if i == self.turn_seat or self.simultaneous else T.LINE_SOFT, width=2)
            f.text((left, top - 22), p.short(14).upper(), 14, p.color, bold=True)
            f.text((box[2], top - 22), f"{self.points[i]} pts · best {self.best[i]}", 13, T.MUTED, bold=True, anchor="ra")
            pad = 10
            cards = B.grid((box[0] + pad, box[1] + pad, box[2] - pad, box[3] - pad), 4, 4, gap=8)
            for k, rect in enumerate(cards):
                rr, cc = divmod(k, 4)
                v = self.boards[i][rr][cc]
                col = TILE_COLORS.get(min(v, 2048), (34, 211, 238))
                f.d.rounded_rectangle(rect, radius=10, fill=col if v else (30, 36, 50))
                if v:
                    size = 30 if v < 100 else (24 if v < 1000 else 20)
                    fg = (16, 20, 28) if v >= 8 else (226, 232, 244)
                    f.text(B.mid(rect), str(v), size, fg, bold=True, anchor="mm")
        legend = (f.board[0], f.board[3] - 34, f.board[2], f.board[3])
        T.inset(f.d, legend, radius=12, fill=(24, 29, 40))
        f.text((f.board[0] + 16, f.board[3] - 17), "SLIDE YOUR OWN BOARD · EQUAL TILES MERGE · FIRST TO 2048 WINS",
               13, T.DIM, bold=True, anchor="lm")


# =============================================================== BATTLESHIP 🚢
class Battleship(Game):
    key = "battleship"
    name = "Battleship"
    tagline = "Hidden fleets, cold blood"
    emoji = "🚢"
    rules = "Your fleet is deployed in secret. Call a square each turn: hit, miss or sunk. Sink the whole enemy fleet to win."

    N = 6
    SHIPS = [3, 2, 2, 1, 1]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fleets = [self._deploy(), self._deploy()]
        self.hits = [set(), set()]       # cells of player i's ships that were struck
        self.shots = [set(), set()]      # cells player i fired at (in the enemy grid)
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last: Optional[tuple[int, int]] = None
        self.last_result = ""

    def _deploy(self) -> list[list[tuple[int, int]]]:
        grid = [[0] * self.N for _ in range(self.N)]
        ships = []
        for size in self.SHIPS:
            for _ in range(200):
                horizontal = self.rng.random() < 0.5
                r = self.rng.randrange(self.N)
                c = self.rng.randrange(self.N)
                cells = [(r, c + k) for k in range(size)] if horizontal else [(r + k, c) for k in range(size)]
                if any(not (0 <= rr < self.N and 0 <= cc < self.N) for rr, cc in cells):
                    continue
                if any(grid[rr][cc] for rr, cc in cells):
                    continue
                if any(grid[rr + dr][cc + dc] for rr, cc in cells for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                       if 0 <= rr + dr < self.N and 0 <= cc + dc < self.N):
                    continue
                for rr, cc in cells:
                    grid[rr][cc] = 1
                ships.append(cells)
                break
        return ships

    def _all_ship_cells(self, seat: int) -> set:
        return {cell for ship in self.fleets[seat] for cell in ship}

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, f"Enemy fleet destroyed in {len(self.shots[self.win_seat or 0])} shots.")

    def status(self) -> str:
        if self.done:
            return f"{self.pname(self.win_seat or 0)} rules the sea"
        hit_rate = len(self.hits[1 - self.turn_seat])
        return f"{self.pname(self.turn_seat)} to fire · {hit_rate}/{sum(self.SHIPS)} hits"

    def prompt(self) -> str:
        return "Pick a row and a column to fire at."

    def _sunk(self, seat: int) -> list[list[tuple[int, int]]]:
        return [ship for ship in self.fleets[seat] if all(cell in self.hits[seat] for cell in ship)]

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Battle over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        rc = self.coord_handle(seat, action)
        if rc is None:
            return ""
        r, c = rc
        enemy = self.other(seat)
        if (r, c) in self.shots[seat]:
            raise InvalidAction("You already fired there.")
        self.shots[seat].add((r, c))
        self.last = (r, c)
        cell = f"{chr(65 + r)}{c + 1}"
        if (r, c) in self._all_ship_cells(enemy):
            self.hits[enemy].add((r, c))
            ship = next(s for s in self.fleets[enemy] if (r, c) in s)
            if all(x in self.hits[enemy] for x in ship):
                self.last_result = "sunk"
                msg = f"{self.pname(seat)} fires {cell} — SUNK 💥"
            else:
                self.last_result = "hit"
                msg = f"{self.pname(seat)} fires {cell} — hit!"
            if self.hits[enemy] >= self._all_ship_cells(enemy):
                self.done = True
                self.win_seat = seat
                return msg + " Fleet destroyed!"
        else:
            self.last_result = "miss"
            msg = f"{self.pname(seat)} fires {cell} — miss"
        self.turn_seat = enemy
        return msg

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        out = []
        for r in range(self.N):
            for c in range(self.N):
                if (r, c) not in self.shots[seat]:
                    out.append(f"p{r}{c}")
        return out

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        enemy = self.other(seat)
        free = [(r, c) for r in range(self.N) for c in range(self.N) if (r, c) not in self.shots[seat]]
        if not free:
            return None
        if difficulty >= 2:
            # finish wounded ships first
            for ship in self.fleets[enemy]:
                struck = [x for x in ship if x in self.hits[enemy]]
                if struck and not all(x in self.hits[enemy] for x in ship):
                    cands = [x for x in ship if x not in self.hits[enemy]]
                    if cands:
                        r, c = cands[0]
                        return f"p{r}{c}"
        if difficulty >= 3:
            free.sort(key=lambda rc: (rc[0] + rc[1]) % 2)
        r, c = free[0] if difficulty >= 4 else self.rng.choice(free)
        return f"p{r}{c}"

    def view(self, seat: int) -> ViewModel:
        sels = self.coord_selects(
            seat, self.N, self.N,
            row_labels=lambda i: f"Row {chr(65 + i)}",
            col_labels=lambda i: f"Column {i + 1}",
            row_placeholder="Row (A–F)",
            col_placeholder="Column (1–6)",
        )
        return self._self_view(seat, selects=sels)

    def draw(self, f) -> None:
        gap = 40
        side = min((708 - gap) / 2 - 6, 470)
        for seat in range(len(self.players)):
            left = f.board[0] + seat * (side + gap) + 6
            top = f.board[1] + (522 - side) / 2 - 6
            box = (left, top, left + side, top + side)
            p = self.players[seat]
            f.text((left, top - 26), f"{p.short(12).upper()} WATERS", 14, p.color, bold=True)
            mine_hits = len(self.hits[seat])
            f.text((box[2], top - 26), f"{mine_hits} hits taken", 12, T.DIM, bold=True, anchor="ra")
            f.d.rounded_rectangle(box, radius=12, fill=(18, 34, 52), outline=p.color if seat == self.turn_seat and not self.done else (36, 54, 78), width=2)
            cells = B.grid((box[0] + 6, box[1] + 6, box[2] - 6, box[3] - 6), self.N, self.N, gap=4)
            sunk_cells = {cell for ship in self._sunk(seat) for cell in ship}
            shooter = self.other(seat)
            for i, rect in enumerate(cells):
                rr, cc = divmod(i, self.N)
                cell = (rr, cc)
                f.d.rounded_rectangle(rect, radius=5, fill=(23, 44, 66))
                cx, cy = B.mid(rect)
                size = rect[2] - rect[0]
                if cell in self.hits[seat]:
                    f.d.rounded_rectangle(rect, radius=5, fill=(92, 40, 46))
                    T.cross(f.d, (cx, cy), size * 0.28, (248, 113, 113), width=4)
                    if cell in sunk_cells:
                        f.d.rounded_rectangle(rect, radius=5, outline=(248, 113, 113), width=2)
                elif cell in self.shots[shooter]:
                    T.disc(f.d, (cx, cy), size * 0.13, (108, 128, 156), shade=False)
                if self.last and cell == self.last and shooter == self.turn_seat:
                    f.d.rounded_rectangle(rect, outline=(255, 255, 255), width=2)
            for rr in range(self.N):
                c0 = cells[rr * self.N]
                f.text((c0[0] + 4, c0[1] + 3), chr(65 + rr), 10, (74, 96, 124), bold=True)
            for cc in range(self.N):
                c0 = cells[(self.N - 1) * self.N + cc]
                f.text((c0[0] + 4, c0[3] - 3), str(cc + 1), 10, (74, 96, 124), bold=True, anchor="lb")

