"""Board classics: Tic-Tac-Toe, Ultimate Tic-Tac-Toe, Connect Four, Reversi."""
from __future__ import annotations

from typing import Optional

from ..core import ai as AI
from ..core.types import Control, InvalidAction, Option, Result, Select, ViewModel
from ..render import boards as B
from ..render import theme as T
from .base import Game

XOX_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def _darken(color, k=0.18):
    return tuple(max(0, int(c * k)) for c in color)


def _mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _board_panel(f, box, outline=(38, 45, 62), fill=(20, 24, 34), radius=18):
    f.d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


# ============================================================== TIC TAC TOE 🎯
class Xox(Game):
    key = "xox"
    name = "Tic-Tac-Toe"
    tagline = "Three in a row wins the round"
    emoji = "🎯"
    rules = "Players alternate tapping a cell. First to line up three marks (row, column or diagonal) takes the round."

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.board: list[Optional[int]] = [None] * 9
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.win_line: tuple[int, int, int] | None = None
        self.moves = 0

    # ------------------------------------------------------------------ rules
    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        if self.win_seat is None:
            return Result(None, "Board full — nobody connected three.")
        return Result(self.win_seat, f"{self.pname(self.win_seat)} connected three in a row.", )

    def status(self) -> str:
        if self.done:
            return "Round over" if self.win_seat is None else f"{self.pname(self.win_seat)} wins the round"
        return f"{self.pname(self.turn_seat)} to move"

    def prompt(self) -> str:
        return "Tap any empty cell. Numbers on the board match the buttons." if not self.done else ""

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("This round is already finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Hold on — it is not your turn.")
        if not action.startswith("c") or not action[1:].isdigit():
            raise InvalidAction("Unknown move.")
        i = int(action[1:])
        if not 0 <= i <= 8:
            raise InvalidAction("That cell does not exist.")
        if self.board[i] is not None:
            raise InvalidAction("That cell is already taken.")
        self.board[i] = seat
        self.moves += 1
        for line in XOX_LINES:
            if all(self.board[k] == seat for k in line):
                self.done, self.win_seat, self.win_line = True, seat, line
                return f"{self.pname(seat)} completes {self._cell_name(line[0])}·{self._cell_name(line[1])}·{self._cell_name(line[2])}"
        if self.moves == 9:
            self.done = True
            return "Board full — draw"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} takes {self._cell_name(i)}"

    @staticmethod
    def _cell_name(i: int) -> str:
        return str(i + 1)

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [f"c{i}" for i, v in enumerate(self.board) if v is None]

    def _evaluate(self, seat: int) -> float:
        score = 0.0
        for line in XOX_LINES:
            mine = sum(1 for k in line if self.board[k] == seat)
            theirs = sum(1 for k in line if self.board[k] is not None and self.board[k] != seat)
            if theirs == 0:
                score += (2 ** mine) * 4
            elif mine == 0:
                score -= (2 ** theirs) * 4
        return score

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        depth = AI.depth_for(difficulty)
        return AI.best_move(self, seat, depth, lambda g, s: g._evaluate(s), self.rng, AI.blunder_for(difficulty), time_budget=1.2)

    def view(self, seat: int) -> ViewModel:
        btns = [Control(f"c{i}", str(i + 1), "", "primary" if self.board[i] is None else "secondary", i // 3) for i in range(9)]
        return self._self_view(seat, btns)

    # ------------------------------------------------------------------- paint
    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=6)
        rects = B.grid(bsq, 3, 3, gap=14)
        active = None if self.done else self.players[self.turn_seat].color
        if active:
            T.glow_box(f.img, f.d, (bsq[0] - 6, bsq[1] - 6, bsq[2] + 6, bsq[3] + 6), _darken(active, 0.45), radius=22, width=2, blur=10)
        win = set(self.win_line) if self.win_line else set()
        for i, r in enumerate(rects):
            owner = self.board[i]
            fill = (27, 32, 46)
            outline = (41, 49, 68)
            if i in win:
                fill = _mix((27, 32, 46), self.players[self.win_seat].color, 0.28)
                outline = self.players[self.win_seat].color
            B.cell(f, r, fill=fill, outline=outline, radius=20, width=2)
            cx, cy = B.mid(r)
            if owner is None:
                f.text((cx, cy + 2), str(i + 1), 40, (49, 58, 80), bold=True, anchor="mm")
            else:
                color = self.players[owner].color
                if owner == 0:
                    T.cross(f.d, (cx, cy), 42, color, width=13)
                else:
                    T.ring(f.d, (cx, cy), 44, color, width=13)



# ==================================================== ULTIMATE TIC TAC TOE 🧠
class UltimateXox(Game):
    key = "ultimate_xox"
    name = "Ultimate Tic-Tac-Toe"
    tagline = "Nine boards. One war."
    emoji = "🧠"
    rules = "Your move sends the opponent to the matching mini-board. Win mini-boards, then line up three of them to win the match."

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.cells: list[Optional[int]] = [None] * 81
        self.sub_win: list[Optional[int]] = [None] * 9
        self.sub_line: list[Optional[tuple]] = [None] * 9
        self.next_board: Optional[int] = None
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.win_line: Optional[tuple] = None
        self.moves = 0

    # ------------------------------------------------------------------ rules
    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        if self.win_seat is None:
            return Result(None, "Every board split — the war ends level.")
        return Result(self.win_seat, f"{self.pname(self.win_seat)} captured the meta board.")

    def status(self) -> str:
        if self.done:
            return "Match over"
        where = "any board" if self.next_board is None else f"board {self.next_board + 1}"
        return f"{self.pname(self.turn_seat)} → {where}"

    def prompt(self) -> str:
        if self.done:
            return ""
        if self.next_board is None:
            return "Pick the mini-board you want to attack, then a cell."
        return "Pick a cell in the highlighted mini-board."

    def _target_board(self, seat: int) -> Optional[int]:
        if self.next_board is not None:
            return self.next_board
        return self.pending.get(seat, {}).get("b")

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("This match is over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if action.startswith("x") and action[1:].isdigit():
            idx = int(action[1:])
            self.pending.setdefault(seat, {})["b"] = idx // 9
            return self.act(seat, f"c:{idx % 9}")
        head, _, rest = action.partition(":")
        val = (rest or head[1:]).strip()
        if head.startswith("b"):
            if self.next_board is not None:
                raise InvalidAction("You must play in the highlighted board.")
            if not val.isdigit():
                raise InvalidAction("Choose a board.")
            b = int(val)
            if not 0 <= b < 9 or self.sub_win[b] is not None:
                raise InvalidAction("That board is already decided.")
            self.pending.setdefault(seat, {})["b"] = b
            return ""
        if not head.startswith("c"):
            raise InvalidAction("Unknown move.")
        b = self._target_board(seat)
        if b is None:
            raise InvalidAction("Choose a mini-board first.")
        if not val.isdigit():
            raise InvalidAction("Choose a cell.")
        c = int(val)
        if not 0 <= c < 9:
            raise InvalidAction("No such cell.")
        idx = b * 9 + c
        if self.cells[idx] is not None:
            raise InvalidAction("Cell already taken.")
        self.cells[idx] = seat
        self.moves += 1
        self.pending.pop(seat, None)

        sub = self.cells[b * 9:(b + 1) * 9]
        for line in XOX_LINES:
            if all(sub[k] == seat for k in line):
                self.sub_win[b], self.sub_line[b] = seat, line
                break
        if self.sub_win[b] is None and all(v is not None for v in sub):
            self.sub_win[b] = -1

        if self.sub_win[b] is None:
            self.next_board = c          # sent to the board matching the cell
        else:
            self.next_board = None

        for line in XOX_LINES:
            vals = [self.sub_win[k] for k in line]
            if vals[0] == vals[1] == vals[2] and vals[0] is not None and vals[0] >= 0:
                self.done, self.win_seat, self.win_line = True, vals[0], line
        if not self.done and all(v is not None for v in self.sub_win):
            self.done = True
            counts = [sum(1 for v in self.sub_win if v == s) for s in range(len(self.players))]
            top = max(counts)
            winners = [s for s, c in enumerate(counts) if c == top]
            self.win_seat = winners[0] if len(winners) == 1 else None
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} plays board {b + 1} cell {c + 1}"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        tb = self._target_board(seat)
        if tb is None:
            out = []
            for b in range(9):
                if self.sub_win[b] is None:
                    out += [f"x{b * 9 + c}" for c in range(9) if self.cells[b * 9 + c] is None]
            return out
        return [f"c{c}" for c in range(9) if self.cells[tb * 9 + c] is None]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        acts = self.legal_actions(seat)
        if not acts:
            return None
        if self.rng.random() < AI.blunder_for(difficulty) or difficulty <= 1:
            return self.rng.choice(acts)
        # greedy: capture a mini-board if possible, otherwise take a centre-ish cell
        best, best_score = acts[0], -1e9
        for a in acts:
            try:
                child = self.clone()
                child.act(seat, a)
            except InvalidAction:
                continue
            gain = 0.0
            for k in range(9):
                if child.sub_win[k] == seat and self.sub_win[k] is None:
                    gain += 60
                if child.sub_win[k] == self.other(seat) and self.sub_win[k] is None:
                    gain -= 45
                if child.sub_win[k] is None:
                    gain += 0.4
            if child.done and child.win_seat == seat:
                gain += 10000
            score = gain + self.rng.random() * (8 if difficulty < 4 else 1)
            if score > best_score:
                best, best_score = a, score
        return best

    def view(self, seat: int) -> ViewModel:
        selects: list[Select] = []
        tb = self._target_board(seat)
        if self.next_board is None and not self.done:
            boards = [Option(f"b:{b}", f"Board {b + 1}", "⬜") for b in range(9) if self.sub_win[b] is None]
            if boards:
                mark = self.pending.get(seat, {}).get("b")
                selects.append(Select(f"Attack board{' · ' + str(mark + 1) if mark is not None else ''}", boards, row=0))
        if tb is not None:
            opts = [Option(f"c:{c}", f"Cell {c + 1}", "▫️") for c in range(9) if self.cells[tb * 9 + c] is None]
            if opts:
                selects.append(Select(f"Place on board {tb + 1}", opts, row=1 if selects else 0))
        return self._self_view(seat, selects=selects)

    # ------------------------------------------------------------------- paint
    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=4)
        outer = B.grid(bsq, 3, 3, gap=16)
        tb = self._target_board(self.turn_seat) if not self.done else None
        for b, orect in enumerate(outer):
            active = (not self.done) and (b == tb or (self.next_board is None and self.sub_win[b] is None))
            strong = (not self.done) and b == tb
            fill = (26, 31, 45) if self.sub_win[b] is None else (20, 24, 33)
            outline = (40, 48, 66)
            if active:
                outline = _mix(self.players[self.turn_seat].color, (40, 48, 66), 0.45)
            f.d.rounded_rectangle(orect, radius=16, fill=fill, outline=outline, width=3 if strong else 2)
            if strong:
                T.glow_box(f.img, f.d, orect, _darken(self.players[self.turn_seat].color, 0.4), radius=16, width=2, blur=8)
            pad = 8
            inner = (orect[0] + pad, orect[1] + pad, orect[2] - pad, orect[3] - pad)
            cells = B.grid(inner, 3, 3, gap=4)
            for c, crect in enumerate(cells):
                owner = self.cells[b * 9 + c]
                B.cell(f, crect, fill=(33, 39, 55) if owner is None else (29, 34, 48), outline=None, radius=8)
                cx, cy = B.mid(crect)
                if owner is None:
                    f.text((cx, cy), f"{c + 1}", 15, (58, 68, 92), bold=True, anchor="mm")
                elif owner == 0:
                    T.cross(f.d, (cx, cy), min(crect[2] - crect[0], crect[3] - crect[1]) * 0.26, self.players[0].color, width=5)
                else:
                    T.ring(f.d, (cx, cy), min(crect[2] - crect[0], crect[3] - crect[1]) * 0.27, self.players[1].color, width=5)
            if self.sub_win[b] is not None and self.sub_win[b] >= 0:
                s = self.sub_win[b]
                ov = (orect[0], orect[1], orect[2], orect[3])
                f.d.rounded_rectangle(ov, radius=16, fill=_mix((20, 24, 33), self.players[s].color, 0.20), outline=self.players[s].color, width=2)
                cx, cy = B.mid(orect)
                if s == 0:
                    T.cross(f.d, (cx, cy), 40, self.players[0].color, width=9)
                else:
                    T.ring(f.d, (cx, cy), 42, self.players[1].color, width=9)
        f.text((f.board[0] + 4, f.board[3] + 4), "", 12, T.DIM)


# ================================================================ CONNECT 4 🔴
class Connect4(Game):
    key = "connect4"
    name = "Connect Four"
    tagline = "Drop discs, build a line of four"
    emoji = "🔴"
    rules = "Pick a column to drop your disc. Four in a row — any direction — wins. Gravity is undefeated."

    COLS, ROWS = 7, 6

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.grid: list[list[Optional[int]]] = [[None] * self.COLS for _ in range(self.ROWS)]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.win_cells: list[tuple[int, int]] = []
        self.last: Optional[tuple[int, int]] = None
        self.moves = 0

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        if self.win_seat is None:
            return Result(None, "The board filled up — stalemate.")
        return Result(self.win_seat, f"{self.pname(self.win_seat)} connected four.")

    def status(self) -> str:
        if self.done:
            return "Round over" if self.win_seat is None else f"{self.pname(self.win_seat)} wins"
        return f"{self.pname(self.turn_seat)} to drop"

    def prompt(self) -> str:
        return "Tap a column button to drop a disc." if not self.done else ""

    def _height(self, c: int) -> int:
        for r in range(self.ROWS - 1, -1, -1):
            if self.grid[r][c] is None:
                return r
        return -1

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if not action.startswith("c") or not action[1:].isdigit():
            raise InvalidAction("Pick a column.")
        c = int(action[1:])
        if not 0 <= c < self.COLS:
            raise InvalidAction("No such column.")
        r = self._height(c)
        if r < 0:
            raise InvalidAction("That column is full.")
        self.grid[r][c] = seat
        self.last = (r, c)
        self.moves += 1
        line = self._line_through(r, c, seat)
        if line:
            self.done, self.win_seat, self.win_cells = True, seat, line
            return f"{self.pname(seat)} connects four!"
        if self.moves == self.COLS * self.ROWS:
            self.done = True
            return "Board full — draw"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} → column {c + 1}"

    def _line_through(self, r: int, c: int, seat: int) -> list[tuple[int, int]]:
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            cells = [(r, c)]
            for sign in (1, -1):
                rr, cc = r + dr * sign, c + dc * sign
                while 0 <= rr < self.ROWS and 0 <= cc < self.COLS and self.grid[rr][cc] == seat:
                    cells.append((rr, cc))
                    rr += dr * sign
                    cc += dc * sign
            if len(cells) >= 4:
                return cells
        return []

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [f"c{c}" for c in range(self.COLS) if self._height(c) >= 0]

    def _evaluate(self, seat: int) -> float:
        score = 0.0
        opp = self.other(seat)
        centre = [self.grid[r][3] for r in range(self.ROWS)]
        score += centre.count(seat) * 6 - centre.count(opp) * 6
        windows = []
        for r in range(self.ROWS):
            for c in range(self.COLS - 3):
                windows.append([(r, c + i) for i in range(4)])
        for c in range(self.COLS):
            for r in range(self.ROWS - 3):
                windows.append([(r + i, c) for i in range(4)])
        for r in range(self.ROWS - 3):
            for c in range(self.COLS - 3):
                windows.append([(r + i, c + i) for i in range(4)])
                windows.append([(r + 3 - i, c + i) for i in range(4)])
        for w in windows:
            vals = [self.grid[r][c] for r, c in w]
            mine = vals.count(seat)
            theirs = vals.count(opp)
            if mine and theirs:
                continue
            if mine:
                score += (2 ** mine)
            elif theirs:
                score -= (2 ** theirs) * 1.1
        return score

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        depth = {1: 1, 2: 2, 3: 4, 4: 6}.get(difficulty, 2)
        return AI.best_move(self, seat, depth, lambda g, s: g._evaluate(s), self.rng, AI.blunder_for(difficulty) * 0.7, time_budget=2.5)

    def view(self, seat: int) -> ViewModel:
        full = {f"c{c}" for c in range(self.COLS) if self._height(c) < 0}
        btns = [Control(f"c{c}", str(c + 1), "", "primary" if f"c{c}" not in full else "secondary", 0 if c < 4 else 1, f"c{c}" in full) for c in range(self.COLS)]
        return self._self_view(seat, btns)

    # ------------------------------------------------------------------- paint
    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=14)
        rects = B.grid(bsq, self.COLS, self.ROWS, gap=9)
        x0 = min(r[0] for r in rects) - 16
        y0 = min(r[1] for r in rects) - 44
        x1 = max(r[2] for r in rects) + 16
        y1 = max(r[3] for r in rects) + 16
        panel = (x0, y0, x1, y1)
        f.d.rounded_rectangle(panel, radius=22, fill=(20, 34, 58), outline=(35, 55, 88), width=3)
        f.d.rounded_rectangle((x0 + 4, y0 + 4, x1 - 4, y0 + 15), radius=8, fill=(29, 47, 78))
        # column numbers
        cols_x = sorted({round((r[0] + r[2]) / 2) for r in rects})
        for c, cx in enumerate(cols_x):
            col = self.players[self.turn_seat].color if (not self.done and self._height(c) >= 0) else (58, 74, 104)
            f.text((cx, y0 + 26), str(c + 1), 19, col, bold=True, anchor="mm")
        win = set(self.win_cells)
        for i, r in enumerate(rects):
            rr, cc = divmod(i, self.COLS)
            owner = self.grid[rr][cc]
            rad = (r[2] - r[0]) / 2
            cx, cy = B.mid(r)
            f.d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(12, 17, 27))
            f.d.ellipse((cx - rad + 2, cy - rad + 2, cx + rad - 2, cy + rad - 2), fill=(15, 21, 33))
            if owner is not None:
                color = self.players[owner].color
                T.disc(f.d, (cx, cy), rad - 3, color)
                f.d.ellipse((cx - rad + 3, cy - rad + 3, cx + rad - 3, cy + rad - 3), outline=_darken(color, 0.6), width=2)
                if (rr, cc) in win:
                    T.ring(f.d, (cx, cy), rad + 1, (255, 255, 255), width=4)
            if self.last == (rr, cc) and owner is not None:
                T.ring(f.d, (cx, cy), rad - 8, _darken(self.players[owner].color, 0.35), width=2)


# =================================================================== REVERSI ⚫
class Reversi(Game):
    key = "reversi"
    name = "Reversi"
    tagline = "Flip discs, own the board"
    emoji = "⚫"
    rules = "Place a disc so it sandwiches enemy discs — they flip to your colour. Most discs when the board locks wins."

    DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.cells = [[0] * 8 for _ in range(8)]
        self.cells[3][3] = 2
        self.cells[4][4] = 2
        self.cells[3][4] = 1
        self.cells[4][3] = 1
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last: Optional[tuple[int, int]] = None
        self.passed: list[int] = []

    # ------------------------------------------------------------------ rules
    def _flips(self, r: int, c: int, seat: int) -> list[tuple[int, int]]:
        me = seat + 1
        if self.cells[r][c]:
            return []
        out: list[tuple[int, int]] = []
        for dr, dc in self.DIRS:
            rr, cc = r + dr, c + dc
            buf = []
            while 0 <= rr < 8 and 0 <= cc < 8 and self.cells[rr][cc] not in (0, me):
                buf.append((rr, cc))
                rr += dr
                cc += dc
            if buf and 0 <= rr < 8 and 0 <= cc < 8 and self.cells[rr][cc] == me:
                out += buf
        return out

    def _moves(self, seat: int) -> dict[str, list[tuple[int, int]]]:
        out = {}
        for r in range(8):
            for c in range(8):
                fl = self._flips(r, c, seat)
                if fl:
                    out[f"p{r}{c}"] = fl
        return out

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        counts = self.counts()
        top = max(counts)
        winners = [i for i, v in enumerate(counts) if v == top]
        if len(winners) == 1:
            return Result(winners[0], f"Final discs {counts[0]} – {counts[1]}.")
        return Result(None, f"Perfectly split {counts[0]} – {counts[1]}.")

    def counts(self) -> list[int]:
        return [sum(row.count(i + 1) for row in self.cells) for i in range(len(self.players))]

    def status(self) -> str:
        if self.done:
            c = self.counts()
            return f"Board locked · {c[0]}–{c[1]}"
        c = self.counts()
        return f"{self.pname(self.turn_seat)} to move · discs {c[0]}–{c[1]}"

    def prompt(self) -> str:
        return "Pick a row below, then a column. Dots mark your legal moves." if not self.done else ""

    def _advance(self) -> None:
        nxt = self.other(self.turn_seat)
        if self._moves(nxt):
            self.turn_seat = nxt
            return
        if self._moves(self.turn_seat):
            return
        self.done = True
        counts = self.counts()
        top = max(counts)
        winners = [i for i, v in enumerate(counts) if v == top]
        self.win_seat = winners[0] if len(winners) == 1 else None

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        cell = self.coord_handle(seat, action)
        if cell is None:
            return ""
        r, c = cell
        flips = self._flips(r, c, seat)
        if not flips:
            raise InvalidAction("That square would not flip anything.")
        self.cells[r][c] = seat + 1
        for rr, cc in flips:
            self.cells[rr][cc] = seat + 1
        self.last = (r, c)
        self._advance()
        return f"{self.pname(seat)} {chr(65 + r)}{c + 1} +{len(flips)}"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return list(self._moves(seat).keys())

    def _evaluate(self, seat: int) -> float:
        me = seat + 1
        opp = self.other(seat) + 1
        corners = [(0, 0), (0, 7), (7, 0), (7, 7)]
        score = 0.0
        for r, c in corners:
            if self.cells[r][c] == me:
                score += 25
            elif self.cells[r][c] == opp:
                score -= 25
        score += len(self._moves(seat)) * 3 - len(self._moves(self.other(seat))) * 3
        score += (sum(row.count(me) for row in self.cells) - sum(row.count(opp) for row in self.cells)) * 0.6
        return score

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        depth = {1: 0, 2: 2, 3: 3, 4: 4}.get(difficulty, 2)
        return AI.best_move(self, seat, depth, lambda g, s: g._evaluate(s), self.rng, AI.blunder_for(difficulty) * 0.6, time_budget=2.2)

    def view(self, seat: int) -> ViewModel:
        sels = self.coord_selects(
            seat, 8, 8,
            row_labels=lambda i: f"Row {chr(65 + i)}",
            col_labels=lambda i: f"Column {i + 1}",
            row_placeholder="Row (A–H)",
            col_placeholder="Column (1–8)",
        )
        return self._self_view(seat, selects=sels)

    # ------------------------------------------------------------------- paint
    def draw(self, f) -> None:
        bsq = B.fit(f.board, 458, 458, anchor="bottom")
        f.d.rounded_rectangle((bsq[0] - 10, bsq[1] - 10, bsq[2] + 10, bsq[3] + 10), radius=16, fill=(17, 62, 48), outline=(28, 92, 70), width=2)
        rects = B.grid(bsq, 8, 8, gap=2)
        legal = self._moves(self.turn_seat) if not self.done else {}
        legal_cells = {k[1:] for k in legal}
        for i, r in enumerate(rects):
            rr, cc = divmod(i, 8)
            B.cell(f, r, fill=(32, 108, 80), outline=None, radius=3)
            cx, cy = B.mid(r)
            size = r[2] - r[0]
            val = self.cells[rr][cc]
            if val:
                color = self.players[val - 1].color
                if val - 1 == 0:
                    color = (238, 240, 250)
                else:
                    color = (26, 30, 40)
                T.disc(f.d, (cx, cy), size * 0.40, color, shade=val - 1 == 0)
                edge = (200, 205, 220) if val - 1 == 0 else (58, 66, 86)
                f.d.ellipse((cx - size * 0.40, cy - size * 0.40, cx + size * 0.40, cy + size * 0.40), outline=edge, width=2)
                if self.last == (rr, cc):
                    f.d.ellipse((cx - size * 0.46, cy - size * 0.46, cx + size * 0.46, cy + size * 0.46), outline=(255, 255, 255), width=2)
            elif str(rr) + str(cc) in legal_cells and not self.done:
                col = self.players[self.turn_seat].color
                T.disc(f.d, (cx, cy), size * 0.14, _mix(col, (32, 108, 80), 0.35), shade=False)
        # disc counters above the board
        counts = self.counts()
        y = f.board[1]
        f.text((f.board[0], y + 2), "DISCS", 12, T.DIM, bold=True)
        cx = f.board[0]
        for i, p in enumerate(self.players):
            box = (cx, y + 20, cx + 210, y + 56)
            T.inset(f.d, box, radius=12, fill=T.CARD_LO, outline=T.LINE_SOFT)
            T.disc(f.d, (cx + 24, y + 39), 11, (238, 240, 250) if i == 0 else (26, 30, 40))
            f.d.ellipse((cx + 13, y + 28, cx + 35, y + 50), outline=(200, 205, 220) if i == 0 else (58, 66, 86), width=1)
            f.text((cx + 44, y + 30), p.short(11), 14, T.MUTED, bold=True)
            f.text((box[2] - 14, y + 39), f"{counts[i]}", 22, T.TEXT, bold=True, anchor="rm")
            cx = box[2] + 10
