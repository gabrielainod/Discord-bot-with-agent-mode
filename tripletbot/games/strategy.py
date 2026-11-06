"""Deep strategy: American Checkers and full-rules Chess."""
from __future__ import annotations

from typing import Optional

import chess

from ..core import ai as AI
from ..core.types import InvalidAction, Option, Result, Select, ViewModel
from ..render import boards as B
from ..render import theme as T
from .base import Game

DIRS4 = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _inside(r, c, n=8):
    return 0 <= r < n and 0 <= c < n


# ================================================================ CHECKERS ⚪
class Checkers(Game):
    key = "checkers"
    name = "Checkers"
    tagline = "Jump, crown, conquer"
    emoji = "⚪"
    rules = "Men move diagonally forward, kings move both ways. Captures are mandatory — chain jumps to wipe a whole row."

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.cells = [[0] * 8 for _ in range(8)]
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    if r < 3:
                        self.cells[r][c] = 3      # seat 1 man
                    elif r > 4:
                        self.cells[r][c] = 1      # seat 0 man
        self.turn_seat = 0
        self.chain_piece: Optional[tuple[int, int]] = None
        self.done = False
        self.win_seat: Optional[int] = None
        self.last: Optional[tuple[int, int]] = None
        self.last_move: Optional[tuple[tuple[int, int], tuple[int, int]]] = None

    # ------------------------------------------------------------------ rules
    @staticmethod
    def _seat_of(v: int) -> int:
        return (v - 1) // 2

    @staticmethod
    def _is_king(v: int) -> bool:
        return (v - 1) % 2 == 1

    def _piece_moves(self, r: int, c: int, board=None):
        b = board if board is not None else self.cells
        v = b[r][c]
        if not v:
            return [], []
        seat, king = self._seat_of(v), self._is_king(v)
        dirs = DIRS4 if king else ([(-1, -1), (-1, 1)] if seat == 0 else [(1, -1), (1, 1)])
        caps, normals = [], []
        for dr, dc in dirs:
            rr, cc = r + dr, c + dc
            if not _inside(rr, cc):
                continue
            if b[rr][cc] == 0:
                normals.append((rr, cc))
            elif self._seat_of(b[rr][cc]) != seat:
                r2, c2 = rr + dr, cc + dc
                if _inside(r2, c2) and b[r2][c2] == 0:
                    caps.append((r2, c2))
        return caps, normals

    def _all_moves(self, seat: int, board=None):
        b = board if board is not None else self.cells
        out = []
        forced = []
        if self.chain_piece and seat == self.turn_seat:
            r, c = self.chain_piece
            caps, _ = self._piece_moves(r, c, b)
            return [((r, c), (rr, cc), True) for rr, cc in caps]
        for r in range(8):
            for c in range(8):
                v = b[r][c]
                if v and self._seat_of(v) == seat:
                    caps, normals = self._piece_moves(r, c, b)
                    forced += [((r, c), (rr, cc), True) for rr, cc in caps]
                    out += [((r, c), (rr, cc), False) for rr, cc in normals]
        return forced if forced else out

    def is_over(self) -> bool:
        return self.done

    def _count(self, seat: int) -> int:
        return sum(1 for r in range(8) for c in range(8) if self.cells[r][c] and self._seat_of(self.cells[r][c]) == seat)

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        if self.win_seat is None:
            return Result(None, "Both armies stalled out.")
        return Result(self.win_seat, f"{self.pname(self.win_seat)} wiped the board.")

    def status(self) -> str:
        if self.done:
            return "Round over" if self.win_seat is None else f"{self.pname(self.win_seat)} wins"
        extra = " · chain jump!" if self.chain_piece else ""
        return f"{self.pname(self.turn_seat)} to move{extra}"

    def prompt(self) -> str:
        return "Pick one of your pieces, then a highlighted square." if not self.done else ""

    def _apply_move(self, seat: int, frm, to) -> str:
        r, c = frm
        rr, cc = to
        caps, _ = self._piece_moves(r, c)
        v = self.cells[r][c]
        captured = None
        if to in caps:
            captured = ((r + rr) // 2, (c + cc) // 2)
            self.cells[captured[0]][captured[1]] = 0
        self.cells[rr][cc] = v
        self.cells[r][c] = 0
        crowned = False
        if not self._is_king(v) and ((seat == 0 and rr == 0) or (seat == 1 and rr == 7)):
            self.cells[rr][cc] = seat * 2 + 2
            crowned = True
        self.last = (rr, cc)
        self.last_move = (frm, to)

        if captured and not crowned:
            more, _ = self._piece_moves(rr, cc)
            if more:
                self.chain_piece = (rr, cc)
                return f"{self.pname(seat)} jumps {chr(97 + cc)}{rr + 1} — chain available!"

        self.chain_piece = None
        self.turn_seat = self.other(seat)
        opp_moves = self._all_moves(self.turn_seat)
        if self._count(self.turn_seat) == 0 or not opp_moves:
            self.done = True
            self.win_seat = seat
        msg = f"{self.pname(seat)} {chr(97 + c)}{r + 1}→{chr(97 + cc)}{rr + 1}"
        if captured:
            msg += " (capture)"
        if crowned:
            msg += " 👑"
        return msg

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if action.startswith("m"):
            frm = (int(action[1]), int(action[2]))
            to = (int(action[3]), int(action[4]))
            legal = self._all_moves(seat)
            if (frm, to, to in self._piece_moves(*frm)[0]) not in legal:
                raise InvalidAction("Illegal move.")
            self.pending.pop(seat, None)
            return self._apply_move(seat, frm, to)
        if action.startswith("p"):
            r, c = int(action[1]), int(action[2])
            v = self.cells[r][c]
            if not v or self._seat_of(v) != seat:
                raise InvalidAction("That is not your piece.")
            if self.chain_piece:
                raise InvalidAction("You must continue the chain jump.")
            caps, normals = self._piece_moves(r, c)
            if not self._all_moves(seat):
                raise InvalidAction("No moves left.")
            if not caps and not normals:
                raise InvalidAction("That piece is stuck.")
            forced = any(m[2] for m in self._all_moves(seat))
            if forced and not caps:
                raise InvalidAction("Captures are mandatory — pick another piece.")
            self.pending[seat] = {"p": (r, c)}
            return ""
        if action.startswith("t"):
            p = self.pending.get(seat, {}).get("p")
            if not p:
                raise InvalidAction("Pick a piece first.")
            to = (int(action[1]), int(action[2]))
            caps, normals = self._piece_moves(*p)
            if to not in caps and to not in normals:
                raise InvalidAction("That square is not reachable.")
            if caps and to not in caps:
                raise InvalidAction("You can capture — captures are mandatory.")
            self.pending.pop(seat, None)
            return self._apply_move(seat, p, to)
        raise InvalidAction("Unknown move.")

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [f"m{a[0][0]}{a[0][1]}{a[1][0]}{a[1][1]}" for a in self._all_moves(seat)]

    def _evaluate(self, seat: int) -> float:
        score = 0.0
        for r in range(8):
            for c in range(8):
                v = self.cells[r][c]
                if not v:
                    continue
                s = self._seat_of(v)
                val = 175.0 if self._is_king(v) else 100.0
                if not self._is_king(v):
                    val += (7 - r) * 6 if s == 0 else r * 6
                val += (3.5 - abs(3.5 - c)) * 3
                score += val if s == seat else -val
        score += len(self._all_moves(seat)) * 4 - len(self._all_moves(self.other(seat))) * 4
        return score

    def move_priority(self, seat: int, action: str) -> float:
        return 3.0 if action.startswith("m") else 0.0

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        depth = {1: 0, 2: 2, 3: 4, 4: 6}.get(difficulty, 2)
        return AI.best_move(self, seat, depth, lambda g, s: g._evaluate(s), self.rng, AI.blunder_for(difficulty) * 0.7, time_budget=2.2)

    def view(self, seat: int) -> ViewModel:
        selects: list[Select] = []
        if not self.done and seat == self.turn_seat:
            moves = self._all_moves(seat)
            forced = any(m[2] for m in moves)
            pieces = sorted({m[0] for m in moves})
            cur = self.pending.get(seat, {}).get("p")
            opts = []
            for r, c in pieces:
                label = f"{chr(97 + c)}{r + 1}"
                if self.cells[r][c] and self._is_king(self.cells[r][c]):
                    label += " ♛"
                opts.append(Option(f"p{r}{c}", label, "🔵"))
            if opts and not self.chain_piece:
                selects.append(Select("Your pieces" + (f" · {chr(97 + cur[1])}{cur[0] + 1}" if cur else ""), opts, row=0))
            targets = []
            if cur:
                caps, normals = self._piece_moves(*cur)
                allowed = caps if forced else normals
                targets = [Option(f"t{r}{c}", f"{chr(97 + c)}{r + 1}", "🎯") for r, c in allowed]
            if targets:
                selects.append(Select("Move to", targets, row=1 if not self.chain_piece else 0))
        return self._self_view(seat, selects=selects)

    # ------------------------------------------------------------------- paint
    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=10)
        rects = B.grid(bsq, 8, 8, gap=0)
        moves = self._all_moves(self.turn_seat) if not self.done else []
        cur = self.pending.get(self.turn_seat, {}).get("p")
        targets = set()
        if cur:
            caps, normals = self._piece_moves(*cur)
            targets = set(self._piece_moves(*cur)[0] or self._piece_moves(*cur)[1])
        for i, r in enumerate(rects):
            rr, cc = divmod(i, 8)
            light = (rr + cc) % 2 == 0
            f.d.rectangle(r, fill=(214, 220, 228) if light else (84, 102, 128))
            cx, cy = B.mid(r)
            size = r[2] - r[0]
            if (rr, cc) in targets:
                f.d.ellipse((cx - size * 0.16, cy - size * 0.16, cx + size * 0.16, cy + size * 0.16), fill=(52, 211, 153))
            v = self.cells[rr][cc]
            if v:
                s = self._seat_of(v)
                color = self.players[s].color
                T.disc(f.d, (cx, cy), size * 0.38, color)
                f.d.ellipse((cx - size * 0.38, cy - size * 0.38, cx + size * 0.38, cy + size * 0.38), outline=tuple(max(0, int(c * 0.55)) for c in color), width=2)
                if self._is_king(v):
                    T.star(f.d, (cx, cy), size * 0.17, (255, 240, 190))
                if self.last_move and self.last_move[1] == (rr, cc):
                    f.d.ellipse((cx - size * 0.46, cy - size * 0.46, cx + size * 0.46, cy + size * 0.46), outline=(255, 255, 255), width=2)
        movable = {m[0] for m in moves}
        for r, c in movable:
            cx, cy = B.mid(rects[r * 8 + c])
            size = rects[0][2] - rects[0][0]
            f.d.ellipse((cx - size * 0.44, cy - size * 0.44, cx + size * 0.44, cy + size * 0.44), outline=(255, 255, 255), width=2)
        for i in range(8):
            f.text((rects[i][0] + 3, rects[i][1] + 2), chr(97 + i), 11, (70, 82, 104), bold=True)
            f.text((rects[56 + i][2] - 3, rects[56 + i][3] - 2), f"{8 - i}", 11, (70, 82, 104), bold=True, anchor="rb")


# =================================================================== CHESS ♞
PIECE_GLYPH = {
    chess.PAWN: "♟", chess.KNIGHT: "♞", chess.BISHOP: "♝",
    chess.ROOK: "♜", chess.QUEEN: "♛", chess.KING: "♚",
}
PIECE_VALUE = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
FILES = "abcdefgh"


class Chess(Game):
    key = "chess"
    name = "Chess"
    tagline = "The real thing — full rules"
    emoji = "♞"
    rules = "Full legal chess: castling, en passant, promotion to queen, checkmate, stalemate and the 50-move rule."

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.board = chess.Board()
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""
        self.last_move: Optional[tuple[int, int]] = None

    # ------------------------------------------------------------------ rules
    @staticmethod
    def _sq(name: str) -> int:
        return chess.parse_square(name)

    @staticmethod
    def _name(sq: int) -> str:
        return chess.square_name(sq)

    def _seat_of_color(self, color: bool) -> int:
        return 0 if color == chess.WHITE else 1

    def _color_of_seat(self, seat: int) -> bool:
        return chess.WHITE if seat == 0 else chess.BLACK

    def is_over(self) -> bool:
        if not self.done and self.board.is_game_over():
            self._finish()
        return self.done

    def _finish(self) -> None:
        outcome = self.board.outcome()
        self.done = True
        if outcome is None or outcome.winner is None:
            self.win_seat = None
            self.reason = "Draw by " + (outcome.termination.name.lower().replace("_", " ") if outcome else "rules")
        else:
            self.win_seat = self._seat_of_color(outcome.winner)
            kind = outcome.termination.name.replace("_", " ").title()
            self.reason = f"{kind} — {self.pname(self.win_seat)} delivers it."

    def result(self) -> Optional[Result]:
        self.is_over()
        if not self.done:
            return None
        return Result(self.win_seat, self.reason)

    def status(self) -> str:
        if self.is_over():
            return "Checkmate" if self.board.is_checkmate() else "Game over"
        who = self.pname(self.turn_seat)
        if self.board.is_check():
            return f"CHECK · {who} must respond"
        return f"{who} to move"

    def prompt(self) -> str:
        return "Pick a piece, then a legal destination." if not self.is_over() else ""

    def act(self, seat: int, action: str) -> str:
        if self.is_over():
            raise InvalidAction("The game is finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if action.startswith("m"):
            try:
                mv = chess.Move.from_uci(action[1:])
            except ValueError:
                raise InvalidAction("Malformed move.")
            if mv not in self.board.legal_moves:
                raise InvalidAction("Illegal move.")
            return self._play(mv)
        if action.startswith("p"):
            sq = self._sq(action[1:])
            piece = self.board.piece_at(sq)
            if not piece or piece.color != self._color_of_seat(seat):
                raise InvalidAction("That is not your piece.")
            if not any(m.from_square == sq for m in self.board.legal_moves):
                raise InvalidAction("That piece has no legal move.")
            self.pending[seat] = {"sq": sq}
            return ""
        if action.startswith("t"):
            frm = self.pending.get(seat, {}).get("sq")
            if frm is None:
                raise InvalidAction("Pick a piece first.")
            to = self._sq(action[1:])
            mv = chess.Move(frm, to)
            if mv not in self.board.legal_moves and chess.Move(frm, to, promotion=chess.QUEEN) in self.board.legal_moves:
                mv = chess.Move(frm, to, promotion=chess.QUEEN)
            if mv not in self.board.legal_moves:
                raise InvalidAction("That move is not legal.")
            self.pending.pop(seat, None)
            return self._play(mv)
        raise InvalidAction("Unknown move.")

    def _play(self, mv: chess.Move) -> str:
        san = self.board.san(mv)
        self.last_move = (mv.from_square, mv.to_square)
        self.board.push(mv)
        self.turn_seat = self.other(self.turn_seat)
        self.is_over()
        msg = f"{san}"
        if self.done:
            msg += " — game over"
        elif self.board.is_check():
            msg += " +"
        return msg

    def legal_actions(self, seat: int) -> list[str]:
        if self.is_over() or seat != self.turn_seat:
            return []
        return [f"m{m.uci()}" for m in self.board.legal_moves]

    def _evaluate(self, seat: int) -> float:
        me = self._color_of_seat(seat)
        score = 0.0
        for sq, piece in self.board.piece_map().items():
            v = PIECE_VALUE[piece.piece_type]
            score += v if piece.color == me else -v
            # mild centralisation bonus
            f_, r_ = chess.square_file(sq), chess.square_rank(sq)
            score += (3.5 - abs(3.5 - f_)) * 2 * (1 if piece.color == me else -1)
            score += (3.5 - abs(3.5 - r_)) * 2 * (1 if piece.color == me else -1)
        score += self.board.legal_moves.count() * 1.5
        return score

    def move_priority(self, seat: int, action: str) -> float:
        try:
            mv = chess.Move.from_uci(action[1:])
        except ValueError:
            return 0
        cap = self.board.piece_at(mv.to_square)
        return PIECE_VALUE.get(cap.piece_type, 0) / 100 if cap else 0.5

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        depth = {1: 1, 2: 2, 3: 2, 4: 3}.get(difficulty, 2)
        if self.board.fullmove_number <= 2 and difficulty <= 3:
            return self.rng.choice(self.legal_actions(seat))
        return AI.best_move(self, seat, depth, lambda g, s: g._evaluate(s), self.rng, AI.blunder_for(difficulty) * 0.5, time_budget=1.3)

    def view(self, seat: int) -> ViewModel:
        selects: list[Select] = []
        if not self.is_over() and seat == self.turn_seat:
            cur = self.pending.get(seat, {}).get("sq")
            sources = sorted({m.from_square for m in self.board.legal_moves})
            opts = []
            for sq in sources:
                p = self.board.piece_at(sq)
                opts.append(Option(f"p{self._name(sq)}", f"{PIECE_GLYPH[p.piece_type]} {self._name(sq).upper()}", ""))
            if opts:
                selects.append(Select("Your pieces", opts, row=0))
            if cur is not None:
                dests = sorted({m.to_square for m in self.board.legal_moves if m.from_square == cur})
                tgt = []
                for sq in dests:
                    cap = self.board.piece_at(sq)
                    label = self._name(sq).upper()
                    emoji = "🎯"
                    if cap:
                        emoji = "⚔️"
                        label += f" · takes {PIECE_GLYPH[cap.piece_type]}"
                    tgt.append(Option(f"t{self._name(sq)}", label, emoji))
                if tgt:
                    selects.append(Select(f"Move {self._name(cur).upper()} to", tgt, row=1))
        return self._self_view(seat, selects=selects, prompt=self.prompt())

    # ------------------------------------------------------------------- paint
    def draw(self, f) -> None:
        bsq = B.square(f.board, pad=10)
        rects = B.grid(bsq, 8, 8, gap=0)
        cur = self.pending.get(self.turn_seat, {}).get("sq")
        dests = {m.to_square for m in self.board.legal_moves if m.from_square == cur} if cur is not None else set()
        check_sq = self.board.king(self.board.turn) if self.board.is_check() else None
        for i, r in enumerate(rects):
            rr, cc = divmod(i, 8)
            sq = chess.square(cc, 7 - rr)
            light = (rr + cc) % 2 == 0
            f.d.rectangle(r, fill=(211, 216, 226) if light else (82, 100, 124))
            if self.last_move and sq in self.last_move:
                f.d.rectangle(r, fill=(196, 186, 108) if light else (120, 116, 68))
            if sq == cur:
                f.d.rectangle(r, outline=(124, 92, 255), width=3)
            if sq == check_sq:
                f.d.rectangle(r, fill=(190, 70, 70), outline=(248, 113, 113), width=3)
            piece = self.board.piece_at(sq)
            cx, cy = B.mid(r)
            size = r[2] - r[0]
            if sq in dests and not piece:
                f.d.ellipse((cx - size * 0.13, cy - size * 0.13, cx + size * 0.13, cy + size * 0.13), fill=(58, 74, 96))
            if piece:
                glyph = PIECE_GLYPH[piece.piece_type]
                if sq in dests:
                    f.d.ellipse((cx - size * 0.45, cy - size * 0.45, cx + size * 0.45, cy + size * 0.45), outline=(52, 211, 153), width=3)
                if piece.color == chess.WHITE:
                    f.text((cx, cy + 3), glyph, int(size * 0.86), (250, 250, 248), bold=True, anchor="mm", stroke=3, stroke_fill=(38, 42, 56))
                else:
                    f.text((cx, cy + 3), glyph, int(size * 0.86), (34, 38, 50), bold=True, anchor="mm", stroke=2, stroke_fill=(198, 206, 220))
        # file / rank labels
        for i in range(8):
            f.text((rects[56 + i][0] + 3, rects[56 + i][3] - 2), FILES[i], 10, (108, 124, 148), bold=True, anchor="lb")
            f.text((rects[i * 8][0] + 3, rects[i * 8][1] + 1), str(8 - i), 10, (108, 124, 148), bold=True)
        # material bar
        vals = {0: 0, 1: 0}
        for sq, piece in self.board.piece_map().items():
            vals[self._seat_of_color(piece.color)] += PIECE_VALUE[piece.piece_type]
        x = f.board[0]
        y = f.board[1] - 2 if bsq[1] - f.board[1] > 30 else f.board[3] + 6
        for i, p in enumerate(self.players):
            txt = f"{p.short(10)}  +{max(0, vals[i] - min(vals.values())) // 100 if vals[i] > min(vals.values()) else 0}"
            f.text((x, y), txt, 13, T.MUTED, bold=True)
            x += 220
