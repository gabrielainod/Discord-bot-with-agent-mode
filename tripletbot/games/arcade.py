"""Arcade games: Type Fast, Reaction Duel, Simon, Rock-Paper-Scissors, Math Duel,
Mastermind and Higher/Lower."""
from __future__ import annotations

import re
import time
from typing import Optional

from ..core.types import Control, InvalidAction, ModalSpec, Option, Result, Select, ViewModel
from ..render import boards as B
from ..render import theme as T
from .base import Game

GREEN, RED, GOLD, BLUE = T.GREEN, T.RED, T.GOLD, T.BLUE

TYPE_WORDS = """
code rat game fast jump blue fire node star wave quiz mind byte loop push kick dash flip grid hive
iron jolt kite lava mint nova opal peak quill rush storm turbo ultra vibe wolf xray yolk zest arcade
pixel turbo blaze comet echo frost glove hyper ivory joker karma laser metro ninja orbit pulse quake
radar sonic tempo unity vivid whale xenon yacht zebra amber brick cedar delta ember fable giant honey
index jelly knoll lemon maple nerd ocean piano queen robot sushi tiger urban venom wagon xerus
""".split()


# ============================================================== TYPE FAST ⌨️
class TypeFast(Game):
    key = "typefast"
    name = "Type Fast"
    tagline = "Sixty seconds of pure typing"
    emoji = "⌨️"
    rules = "A word appears for each player. Type it correctly to score and get the next one. Most words in 60 seconds wins."
    simultaneous = True
    timed = True
    DURATION = 60

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.words = [self._pick() for _ in self.players]
        self.points = [0 for _ in self.players]
        self.misses = [0 for _ in self.players]
        self.done = False
        self.win_seat: Optional[int] = None
        self.deadline = time.monotonic() + self.DURATION
        self.last: Optional[tuple[int, str, bool]] = None
        self.reason = ""

    def _pick(self) -> str:
        return self.rng.choice(TYPE_WORDS)

    def acting(self) -> list[int]:
        return [] if self.is_over() else [p.index for p in self.players]

    def turn(self) -> int:
        return -1

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def tick(self, now: float) -> bool:
        if not self.done and now >= self.deadline:
            self.done = True
            top = max(self.points)
            w = [i for i, v in enumerate(self.points) if v == top]
            self.win_seat = w[0] if len(w) == 1 else None
            self.reason = f"Time! Words typed: {' – '.join(str(p) for p in self.points)}."
            return True
        return False

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason)

    def status(self) -> str:
        if self.done:
            return "Time!"
        return f"{int(self.remaining())}s left · {self.points[0]} – {self.points[1]} words"

    def prompt(self) -> str:
        return "Type your word exactly, then send."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Time is up.")
        typed = (action[1:] if action.startswith("g") else action).strip().lower()
        if not typed:
            raise InvalidAction("Type a word.")
        if typed != self.words[seat]:
            self.misses[seat] += 1
            self.last = (seat, typed, False)
            raise InvalidAction(f"Not quite — your word is “{self.words[seat].upper()}”.")
        self.points[seat] += 1
        self.last = (seat, self.words[seat], True)
        self.words[seat] = self._pick()
        return f"{self.pname(seat)} types “{typed.upper()}” (+1)"

    def legal_actions(self, seat: int) -> list[str]:
        return []

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        return "g" + self.words[seat]

    def view(self, seat: int) -> ViewModel:
        modal = None
        if not self.done:
            modal = ModalSpec("g", "Type it", "Your word", self.words[seat], "", 20, "Type word", "⌨️", 0)
        return self._self_view(seat, modal=modal)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        rem = self.remaining()
        bar = (x0 + 10, y0 + 8, x1 - 10, y0 + 26)
        T.rounded_progress(f.d, bar, rem / self.DURATION, GREEN if rem > 15 else RED)
        f.text((bar[0] + 6, bar[1] + 9), f"{int(rem)}s", 12, (16, 20, 28), bold=True, anchor="lm")
        lanes = len(self.players)
        lh = (y1 - bar[3] - 24) / lanes
        for i, p in enumerate(self.players):
            top = bar[3] + 16 + i * lh
            box = (x0 + 10, top, x1 - 10, top + lh - 10)
            f.d.rounded_rectangle(box, radius=16, fill=(29, 35, 50), outline=p.color, width=2)
            f.text((box[0] + 18, box[1] + 16), p.short(14).upper(), 14, p.color, bold=True)
            f.text((box[2] - 18, box[1] + 14), f"{self.points[i]}", 34, T.TEXT, bold=True, anchor="ra")
            word = self.words[i].upper()
            f.d.rounded_rectangle((box[0] + 18, box[1] + 40, box[0] + 320, box[3] - 14), radius=12, fill=(20, 25, 36), outline=(48, 58, 80))
            f.text((box[0] + 30, (box[1] + 40 + box[3] - 14) / 2), word, 34, T.TEXT, bold=True, anchor="lm", mono=True)
            f.text((box[0] + 340, box[1] + 52), f"{self.misses[i]} misses", 13, T.DIM, bold=True)
            if self.last and self.last[0] == i:
                ok = self.last[2]
                f.text((box[0] + 340, box[1] + 74), ("✓ " if ok else "✗ ") + self.last[1].upper()[:12], 15, GREEN if ok else RED, bold=True)


# ============================================================ REACTION DUEL ⚡
class Reaction(Game):
    key = "reaction"
    name = "Reaction Duel"
    tagline = "Green means go. Red costs you."
    emoji = "⚡"
    rules = "Three rounds. Watch the panel: when it turns green, hit the button first. Tap early and you forfeit the round."
    simultaneous = True
    timed = True
    max_players = 4
    ROUNDS = 3

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.round = 1
        self.state = "wait"            # wait | go | break | done
        self.t = time.monotonic()
        self.go_at = self.t + self.rng.uniform(2.5, 5.0)
        self.go_time: Optional[float] = None
        self.next_at = 0.0
        self.wins = [0 for _ in self.players]
        self.times: dict[int, float] = {}
        self.done = False
        self.win_seat: Optional[int] = None
        self.round_winner: Optional[int] = None
        self.message = "Wait for green…"
        self.reason = ""

    def acting(self) -> list[int]:
        return [] if self.is_over() else [p.index for p in self.players]

    def turn(self) -> int:
        return -1

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason or f"Rounds won: {' – '.join(str(w) for w in self.wins)}")

    def status(self) -> str:
        if self.done:
            return self.reason or "Duel over"
        if self.state == "wait":
            return f"Round {self.round} · hold…"
        if self.state == "go":
            return f"Round {self.round} · GO!"
        return f"Round {self.round} · {self.message}"

    def prompt(self) -> str:
        if self.state == "go":
            return "TAP NOW!"
        if self.state == "wait":
            return "Do not tap yet…"
        return "Next round starting…"

    def tick(self, now: float) -> bool:
        if self.done:
            return False
        if self.state == "wait" and now >= self.go_at:
            self.state = "go"
            self.go_time = now
            self.message = "GO!"
            return True
        if self.state == "go" and self.go_time and now - self.go_time > 2.5:
            self._end_round(None, "Nobody moved in time")
            return True
        if self.state == "break" and now >= self.next_at:
            if self.round >= self.ROUNDS:
                self._finish()
            else:
                self.round += 1
                self.state = "wait"
                self.times = {}
                self.round_winner = None
                self.message = "Wait for green…"
                self.go_at = now + self.rng.uniform(2.0, 4.5)
            return True
        return False

    def _end_round(self, winner: Optional[int], msg: str) -> None:
        self.round_winner = winner
        if winner is not None:
            self.wins[winner] += 1
        self.state = "break"
        self.next_at = time.monotonic() + 2.2
        self.message = msg

    def _finish(self) -> None:
        self.done = True
        top = max(self.wins)
        w = [i for i, v in enumerate(self.wins) if v == top]
        self.win_seat = w[0] if len(w) == 1 and top > 0 else None
        self.reason = f"Rounds won: {' – '.join(str(x) for x in self.wins)}"

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Duel over.")
        if action != "go":
            raise InvalidAction("Just tap the button.")
        now = time.monotonic()
        if self.state == "wait":
            self._end_round(self.other(seat) if len(self.players) == 2 else None,
                            f"{self.pname(seat)} jumped early — foul!")
            return f"{self.pname(seat)} jumps the gun"
        if self.state == "go" and self.go_time:
            dt = now - self.go_time
            self.times[seat] = dt
            self._end_round(seat, f"{self.pname(seat)} reacts in {int(dt * 1000)} ms!")
            return f"{self.pname(seat)} reacts in {int(dt * 1000)} ms"
        raise InvalidAction("Wait for the next round.")

    def legal_actions(self, seat: int) -> list[str]:
        return []

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        # bots only ever tap once the panel is green; the host clock paces them
        if self.state != "go":
            return None
        if self.rng.random() < {1: 0.25, 2: 0.45, 3: 0.7, 4: 0.9}.get(difficulty, 0.6):
            return "go"
        return None

    def ai_delay(self) -> float:
        return 0.22

    def view(self, seat: int) -> ViewModel:
        btns = [Control("go", "TAP", "⚡", "danger" if self.state != "go" else "success", 0)]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        color = {"wait": (120, 44, 46), "go": (26, 120, 88), "break": (34, 40, 56), "done": (34, 40, 56)}[self.state]
        f.d.rounded_rectangle((x0 + 10, y0 + 10, x1 - 10, y1 - 130), radius=20, fill=color, outline=tuple(min(255, c + 40) for c in color), width=3)
        label = {"wait": "WAIT", "go": "GO!", "break": "ROUND OVER", "done": "DONE"}[self.state]
        f.text(((x0 + x1) / 2, (y0 + 10 + y1 - 130) / 2 - 10), label, 84, T.TEXT, bold=True, anchor="mm")
        f.text(((x0 + x1) / 2, (y0 + 10 + y1 - 130) / 2 + 62), self.message, 20, (235, 240, 250), bold=True, anchor="mm")
        # player rows
        for i, p in enumerate(self.players):
            bx = x0 + 10 + i * ((x1 - x0 - 20) / len(self.players))
            box = (bx, y1 - 110, bx + (x1 - x0 - 20) / len(self.players) - 10, y1 - 10)
            f.d.rounded_rectangle(box, radius=14, fill=(29, 35, 50), outline=p.color if self.round_winner == i else T.LINE_SOFT, width=2)
            f.text((box[0] + 14, box[1] + 12), p.short(12), 15, T.MUTED, bold=True)
            f.text((box[0] + 14, box[1] + 40), str(self.wins[i]), 34, T.TEXT, bold=True)
            f.text((box[0] + 44, box[1] + 56), "rounds", 12, T.DIM, bold=True)
            if i in self.times:
                f.text((box[2] - 14, box[1] + 44), f"{int(self.times[i] * 1000)} ms", 16, p.color, bold=True, anchor="ra")


# ================================================================== SIMON 🎛️
PAD_COLORS = [(52, 211, 153), (255, 199, 84), (96, 165, 250), (248, 113, 113)]
PAD_NAMES = ["GREEN", "YELLOW", "BLUE", "RED"]


class Simon(Game):
    key = "simon"
    name = "Simon"
    tagline = "Repeat the pattern, faster than your rival"
    emoji = "🎛️"
    rules = "A pattern appears. Tap the pads in that exact order as fast as you can — first to finish wins the round, a wrong tap eliminates you."

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        length = 4 + self.round_no
        self.seq = [self.rng.randrange(4) for _ in range(length)]
        self.progress = [0 for _ in self.players]
        self.out = [False for _ in self.players]
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""
        self.started = time.monotonic()
        self.times: dict[int, float] = {}

    def acting(self) -> list[int]:
        if self.done:
            return []
        return [i for i in range(len(self.players)) if not self.out[i]]

    def turn(self) -> int:
        return -1

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason or "Pattern cleared.")

    def status(self) -> str:
        if self.done:
            return self.reason or "Round over"
        alive = [i for i, o in enumerate(self.out) if not o]
        return f"{len(self.seq)} steps · {len(alive)} in play"

    def prompt(self) -> str:
        return "Tap the pads in order: " + " ".join(PAD_NAMES[c] for c in self.seq)

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round over.")
        if self.out[seat]:
            raise InvalidAction("You are out of this round.")
        if not action.startswith("p") or not action[1:].isdigit():
            raise InvalidAction("Tap a pad.")
        pad = int(action[1:])
        step = self.progress[seat]
        if pad != self.seq[step]:
            self.out[seat] = True
            if all(self.out):
                self.done = True
                self.reason = "Everyone tripped — nobody survives the pattern."
            elif len(self.players) - sum(self.out) == 1:
                survivor = [i for i, o in enumerate(self.out) if not o][0]
                self.done = True
                self.win_seat = survivor
                self.reason = f"{self.pname(survivor)} is the last one standing."
            return f"{self.pname(seat)} taps wrong at step {step + 1}"
        self.progress[seat] += 1
        if self.progress[seat] >= len(self.seq):
            self.done = True
            self.win_seat = seat
            self.times[seat] = time.monotonic() - self.started
            self.reason = f"{self.pname(seat)} cleared {len(self.seq)} steps."
            return f"{self.pname(seat)} nails the pattern!"
        return f"{self.pname(seat)} → step {self.progress[seat]}/{len(self.seq)}"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or self.out[seat]:
            return []
        return [f"p{i}" for i in range(4)]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        if self.done or self.out[seat]:
            return None
        step = self.progress[seat]
        if difficulty <= 1 and self.rng.random() < 0.12:
            return f"p{(self.seq[step] + 1) % 4}"
        return f"p{self.seq[step]}"

    def view(self, seat: int) -> ViewModel:
        btns = [Control(f"p{i}", PAD_NAMES[i].title(), "", ["success", "secondary", "primary", "danger"][i], i // 2) for i in range(4)]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        # pattern strip
        f.text((x0 + 8, y0 + 4), f"PATTERN · {len(self.seq)} STEPS", 13, T.DIM, bold=True)
        n = len(self.seq)
        step_w = min(46, (x1 - x0 - 20) / max(1, n))
        for i, pad in enumerate(self.seq):
            box = (x0 + 10 + i * step_w, y0 + 26, x0 + 10 + i * step_w + step_w - 6, y0 + 66)
            f.d.rounded_rectangle(box, radius=8, fill=PAD_COLORS[pad])
            f.text(B.mid(box)[0:2], str(i + 1), 13, (18, 22, 30), bold=True, anchor="mm")
        # pads
        pads = B.grid((x0 + 10, y0 + 90, x1 - 10, y0 + 90 + 320), 2, 2, gap=12)
        for i, r in enumerate(pads):
            f.d.rounded_rectangle(r, radius=18, fill=PAD_COLORS[i], outline=tuple(min(255, c + 30) for c in PAD_COLORS[i]), width=2)
            f.text(B.mid(r), PAD_NAMES[i], 20, (16, 20, 28), bold=True, anchor="mm")
        # progress
        y = y0 + 430
        for i, p in enumerate(self.players):
            box = (x0 + 10, y, x1 - 10, y + 44)
            f.d.rounded_rectangle(box, radius=12, fill=T.CARD_LO, outline=p.color if not self.out[i] and not self.done else T.LINE_SOFT, width=2)
            f.text((box[0] + 14, box[1] + 22), p.short(14), 15, T.MUTED if self.out[i] else T.TEXT, bold=True, anchor="lm")
            T.rounded_progress(f.d, (box[0] + 220, box[1] + 16, box[2] - 60, box[1] + 28), self.progress[i] / len(self.seq), p.color)
            label = "OUT" if self.out[i] else f"{self.progress[i]}/{len(self.seq)}"
            f.text((box[2] - 14, box[1] + 22), label, 14, RED if self.out[i] else T.TEXT, bold=True, anchor="rm")
            y += 52


# ================================================= ROCK PAPER SCISSORS ✊
CHOICES = ["rock", "paper", "scissors"]
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


def draw_hand(d, center, r, choice: str, color):
    cx, cy = center
    if choice == "rock":
        d.ellipse((cx - r, cy - r * 0.85, cx + r, cy + r * 0.85), fill=color)
        for k in range(3):
            d.ellipse((cx - r * 0.75 + k * r * 0.52, cy - r * 0.95, cx - r * 0.35 + k * r * 0.52, cy - r * 0.45), fill=color)
    elif choice == "paper":
        d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=int(r * 0.3), fill=color)
        for k in range(3):
            d.line((cx - r * 0.6, cy - r * 0.35 + k * r * 0.42, cx + r * 0.6, cy - r * 0.35 + k * r * 0.42), fill=(20, 24, 34), width=3)
    else:
        d.line((cx - r, cy + r, cx + r, cy - r), fill=color, width=max(6, int(r * 0.28)))
        d.line((cx - r, cy - r, cx + r, cy + r), fill=color, width=max(6, int(r * 0.28)))
        d.ellipse((cx - r * 0.95, cy + r * 0.6, cx - r * 0.35, cy + r * 1.02), outline=color, width=max(4, int(r * 0.16)))
        d.ellipse((cx + r * 0.35, cy + r * 0.6, cx + r * 0.95, cy + r * 1.02), outline=color, width=max(4, int(r * 0.16)))


class RPS(Game):
    key = "rps"
    name = "Rock Paper Scissors"
    tagline = "Best mind game in history"
    emoji = "✊"
    rules = "Everyone picks in secret. Rock beats scissors, scissors beats paper, paper beats rock. Numbers decide multi-player chaos."
    simultaneous = True
    max_players = 4

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.picks: dict[int, str] = {}
        self.scores_local = [0 for _ in self.players]
        self.done = False
        self.win_seat: Optional[int] = None
        self.round_winner: Optional[int] = None
        self.reason = ""
        self.revealed = False

    def acting(self) -> list[int]:
        return [] if self.is_over() else [p.index for p in self.players if p.index not in self.picks]

    def turn(self) -> int:
        return -1

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason or "Throws resolved.")

    def status(self) -> str:
        if self.done:
            return self.reason or "Round over"
        return f"{len(self.picks)}/{len(self.players)} picks locked"

    def prompt(self) -> str:
        return "Pick in secret — the frame reveals when everyone is in."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round over.")
        choice = action[1:] if action.startswith("p") else action
        if choice not in CHOICES:
            raise InvalidAction("Rock, paper or scissors.")
        if seat in self.picks:
            raise InvalidAction("You already picked.")
        self.picks[seat] = choice
        if len(self.picks) < len(self.players):
            return f"{self.pname(seat)} locks a pick"
        return self._resolve()

    def _resolve(self) -> str:
        self.revealed = True
        picks = self.picks
        winners = [s for s in picks if all(picks[s] == picks[o] or BEATS[picks[s]] == picks[o] for o in picks if o != s)]
        if len(winners) == 1:
            self.round_winner = winners[0]
            self.done = True
            self.win_seat = winners[0]
            self.reason = f"{self.pname(winners[0])} wins with {picks[winners[0]].upper()}."
            self.scores_local[winners[0]] += 1
            return self.reason
        self.done = True
        self.win_seat = None
        self.reason = "Identical minds — the round is a draw."
        return self.reason

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat in self.picks:
            return []
        return [f"p{c}" for c in CHOICES]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        if difficulty <= 1:
            return "p" + self.rng.choice(CHOICES)
        # counter the most common human choice pattern (RPS psychology)
        return "p" + self.rng.choice(CHOICES)

    def view(self, seat: int) -> ViewModel:
        btns = [
            Control("prock", "Rock", "✊", "secondary", 0),
            Control("ppaper", "Paper", "✋", "secondary", 0),
            Control("pscissors", "Scissors", "✌️", "secondary", 0),
        ]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        n = len(self.players)
        gap = 24
        w = (x1 - x0 - gap * (n - 1) - 20) / n
        for i, p in enumerate(self.players):
            bx = x0 + 10 + i * (w + gap)
            box = (bx, y0 + 30, bx + w, y1 - 30)
            win = self.revealed and self.round_winner == i
            f.d.rounded_rectangle(box, radius=18, fill=(29, 35, 50), outline=p.color if win else T.LINE_SOFT, width=3 if win else 2)
            if win:
                T.glow_box(f.img, f.d, box, tuple(c // 3 for c in p.color), radius=18, width=2, blur=10)
            f.text((bx + w / 2, box[1] + 26), p.short(14), 17, T.MUTED, bold=True, anchor="ma")
            choice = self.picks.get(i)
            cx, cy = bx + w / 2, (box[1] + box[3]) / 2
            if choice and self.revealed:
                draw_hand(f.d, (cx, cy), min(w, box[3] - box[1]) * 0.22, choice, p.color)
                f.text((cx, box[3] - 34), choice.upper(), 18, T.TEXT, bold=True, anchor="mm")
            elif choice:
                f.d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), outline=p.color, width=3)
                f.text((cx, cy), "✓", 34, p.color, bold=True, anchor="mm")
                f.text((cx, box[3] - 34), "LOCKED", 15, T.DIM, bold=True, anchor="mm")
            else:
                f.text((cx, cy), "?", 64, (58, 68, 90), bold=True, anchor="mm")
                f.text((cx, box[3] - 34), "THINKING", 15, T.DIM, bold=True, anchor="mm")
        if self.revealed:
            T.vs_badge(f.d, ((x0 + x1) / 2, y0 + 20), 16)


# ================================================================ MATH DUEL ➗
class MathDuel(Game):
    key = "mathduel"
    name = "Math Duel"
    tagline = "Mental arithmetic at gunpoint"
    emoji = "➗"
    rules = "Alternating turns, ten quick equations. Pick the right answer to score. Speed is not measured — accuracy is."
    max_players = 4
    N = 10

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.points = [0 for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.index = 0
        self.last: Optional[tuple[int, bool]] = None
        self.q = self._new_question()

    def _new_question(self):
        op = self.rng.choice(["+", "-", "×", "×", "+", "÷"])
        if op == "+":
            a, b = self.rng.randint(12, 89), self.rng.randint(11, 79)
            ans = a + b
        elif op == "-":
            a, b = self.rng.randint(30, 99), self.rng.randint(5, 29)
            ans = a - b
        elif op == "×":
            a, b = self.rng.randint(3, 12), self.rng.randint(3, 12)
            ans = a * b
        else:
            b = self.rng.randint(2, 9)
            ans = self.rng.randint(2, 12)
            a = b * ans
        options = {ans}
        while len(options) < 4:
            delta = self.rng.choice([-12, -9, -6, -3, -2, -1, 1, 2, 3, 6, 9, 12])
            cand = ans + delta
            if cand > 0 and cand != ans:
                options.add(cand)
        opts = sorted(options)
        self.rng.shuffle(opts)
        return (f"{a} {op} {b}", opts, opts.index(ans))

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        top = max(self.points)
        w = [i for i, v in enumerate(self.points) if v == top]
        if len(w) == 1:
            return Result(w[0], f"Correct answers: {' – '.join(str(p) for p in self.points)}")
        return Result(None, "Dead heat in arithmetic.")

    def status(self) -> str:
        if self.done:
            return "Ten questions done"
        return f"{self.pname(self.turn_seat)} · question {self.index + 1}/{self.N}"

    def prompt(self) -> str:
        return "Tap the right answer."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Duel finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if not action.startswith("a") or not action[1:].isdigit():
            raise InvalidAction("Pick an answer.")
        pick = int(action[1:])
        expr, opts, answer = self.q
        if not 0 <= pick < 4:
            raise InvalidAction("No such answer.")
        correct = pick == answer
        if correct:
            self.points[seat] += 1
        self.last = (seat, correct)
        self.index += 1
        self.q = self._new_question()
        if self.index >= self.N:
            self.done = True
            top = max(self.points)
            w = [i for i, v in enumerate(self.points) if v == top]
            self.win_seat = w[0] if len(w) == 1 else None
            return f"{self.pname(seat)} {'scores' if correct else 'misses'} — duel over"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} {'scores' if correct else 'misses'} on {expr}"

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        expr, opts, answer = self.q
        if self.rng.random() < {1: 0.55, 2: 0.75, 3: 0.92, 4: 0.99}.get(difficulty, 0.75):
            return f"a{answer}"
        wrong = [i for i in range(4) if i != answer]
        return f"a{self.rng.choice(wrong)}"

    def view(self, seat: int) -> ViewModel:
        expr, opts, answer = self.q
        btns = [Control(f"a{i}", str(o), "", "primary", i // 2) for i, o in enumerate(opts)]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        expr, opts, answer = self.q
        box = (x0 + 40, y0 + 10, x1 - 40, y0 + 150)
        f.d.rounded_rectangle(box, radius=20, fill=(30, 36, 52), outline=(52, 62, 86), width=2)
        f.text(B.mid(box), expr + " = ?", 62, T.TEXT, bold=True, anchor="mm", mono=True)
        cards = B.grid((x0 + 40, y0 + 180, x1 - 40, y1 - 10), 2, 2, gap=16)
        for i, r in enumerate(cards):
            f.d.rounded_rectangle(r, radius=16, fill=(34, 41, 58), outline=(58, 68, 92), width=2)
            f.text(B.mid(r), str(opts[i]), 46, T.TEXT, bold=True, anchor="mm", mono=True)
        for i, p in enumerate(self.players):
            f.text((x0 + 50 + i * 240, y0 + 162), f"{p.short(12)} {self.points[i]}", 15, p.color if i == self.turn_seat else T.DIM, bold=True)


# ============================================================= MASTERMIND 🎨
MM_COLORS = [(248, 113, 113), (52, 211, 153), (96, 165, 250), (255, 199, 84), (167, 139, 250), (251, 146, 60)]
MM_NAMES = ["Red", "Green", "Blue", "Yellow", "Purple", "Orange"]


class Mastermind(Game):
    key = "mastermind"
    name = "Mastermind"
    tagline = "Crack the four-colour code"
    emoji = "🎨"
    rules = "Four hidden pegs from six colours. Build a guess each turn: black = right colour right spot, white = right colour wrong spot."
    max_players = 2
    SLOTS = 4
    TRIES = 10

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.secret = [self.rng.randrange(6) for _ in range(self.SLOTS)]
        self.guesses: list[list[list[int]]] = [[] for _ in self.players]
        self.feedback: list[list[tuple[int, int]]] = [[] for _ in self.players]
        self.pending: dict[int, list[Optional[int]]] = {}
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason)

    def status(self) -> str:
        if self.done:
            return self.reason
        return f"{self.pname(self.turn_seat)} · guess {len(self.guesses[self.turn_seat]) + 1}/{self.TRIES}"

    def prompt(self) -> str:
        p = self.pending.get(self.turn_seat, [None] * self.SLOTS)
        filled = sum(1 for x in p if x is not None)
        return f"Set {self.SLOTS - filled} more peg(s), then submit." if filled < self.SLOTS else "Ready — hit Submit guess."

    def _score(self, guess: list[int]) -> tuple[int, int]:
        exact = sum(1 for g, s in zip(guess, self.secret) if g == s)
        pool = [s for g, s in zip(guess, self.secret) if g != s]
        guess_pool = [g for g, s in zip(guess, self.secret) if g != s]
        partial = 0
        for c in list(guess_pool):
            if c in pool:
                pool.remove(c)
                guess_pool.remove(c)
                partial += 1
        return exact, partial

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Code already cracked.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if action.startswith("s") and ":" in action:
            _, _, rest = action.partition(":")
            slot_s, _, col_s = rest.partition("=")
            if not slot_s.isdigit() or not col_s.isdigit():
                raise InvalidAction("Bad peg.")
            slot, col = int(slot_s), int(col_s)
            if not (0 <= slot < self.SLOTS and 0 <= col < 6):
                raise InvalidAction("Bad peg.")
            p = self.pending.setdefault(seat, [None] * self.SLOTS)
            p[slot] = col
            return ""
        guess: Optional[list[int]] = None
        if action.startswith("g") and len(action) == 1 + self.SLOTS:
            try:
                guess = [int(ch) for ch in action[1:]]
            except ValueError:
                guess = None
            if guess and any(not 0 <= x < 6 for x in guess):
                guess = None
        if action == "submit" or guess:
            if guess is None:
                p = self.pending.get(seat, [])
                if len(p) < self.SLOTS or any(x is None for x in p):
                    raise InvalidAction("Fill all four pegs first.")
                guess = list(p)
            self.pending.pop(seat, None)
            self.guesses[seat].append(guess)
            ex, pa = self._score(guess)
            self.feedback[seat].append((ex, pa))
            if ex == self.SLOTS:
                self.done, self.win_seat = True, seat
                self.reason = f"{self.pname(seat)} cracked it in {len(self.guesses[seat])} guesses."
                return self.reason
            if all(len(g) >= self.TRIES for g in self.guesses):
                self.done = True
                self.win_seat = None
                self.reason = "Out of guesses — the code survives."
                return "Nobody cracked the code"
            self.turn_seat = self.other(seat)
            return f"{self.pname(seat)} guesses · {ex} exact, {pa} close"
        raise InvalidAction("Unknown action.")

    def legal_actions(self, seat: int) -> list[str]:
        return []

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        tried = {tuple(g) for gs in self.guesses for g in gs}
        all_codes = [[a, b, c, d] for a in range(6) for b in range(6) for c in range(6) for d in range(6)]
        if difficulty >= 2:
            cands = []
            for code in all_codes:
                ok = True
                for gs, fb in zip(self.guesses, self.feedback):
                    for g, (ex, pa) in zip(gs, fb):
                        if self._score_against(code, g) != (ex, pa):
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    cands.append(code)
            if cands:
                if difficulty >= 4:
                    # pick a code that also splits the remaining set well
                    best = cands[0]
                    best_score = -1
                    sample = cands[: min(40, len(cands))]
                    for code in sample:
                        buckets = {}
                        for other_code in cands:
                            key = self._score_against(code, other_code)
                            buckets[key] = buckets.get(key, 0) + 1
                        worst = max(buckets.values())
                        score = -worst
                        if score > best_score:
                            best, best_score = code, score
                    return "g" + "".join(str(x) for x in best)
                return "g" + "".join(str(x) for x in self.rng.choice(cands))
        for _ in range(40):
            code = [self.rng.randrange(6) for _ in range(self.SLOTS)]
            if tuple(code) not in tried:
                return "g" + "".join(str(x) for x in code)
        return "g" + "".join(str(self.rng.randrange(6)) for _ in range(self.SLOTS))

    def _score_against(self, guess: list[int], secret: list[int]) -> tuple[int, int]:
        exact = sum(1 for g, s in zip(guess, secret) if g == s)
        pool = [s for g, s in zip(guess, secret) if g != s]
        gp = [g for g, s in zip(guess, secret) if g != s]
        partial = 0
        for c in list(gp):
            if c in pool:
                pool.remove(c)
                gp.remove(c)
                partial += 1
        return exact, partial

    def view(self, seat: int) -> ViewModel:
        if self.done or seat != self.turn_seat:
            return self._self_view(seat)
        p = self.pending.setdefault(seat, [None] * self.SLOTS)
        sels = []
        for slot in range(self.SLOTS):
            opts = [Option(f"s{slot}:{c}", MM_NAMES[c], "") for c in range(6)]
            cur = p[slot]
            label = f"Peg {slot + 1}" + (f" · {MM_NAMES[cur]}" if cur is not None else "")
            sels.append(Select(label, opts, row=slot))
        btn = Control("submit", "Submit guess", "✅", "success", 4)
        return self._self_view(seat, [btn], sels)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        n = len(self.players)
        colw = (x1 - x0) / n
        for s in range(n):
            bx = x0 + s * colw + 10
            p = self.players[s]
            f.text((bx, y0 + 4), p.short(14).upper(), 14, p.color if s == self.turn_seat and not self.done else T.MUTED, bold=True)
            rows = self.TRIES
            rh = min(34, (y1 - y0 - 60) / rows)
            for r in range(rows):
                ry = y0 + 30 + r * rh
                if r < len(self.guesses[s]):
                    g = self.guesses[s][r]
                    ex, pa = self.feedback[s][r]
                    for c, code in enumerate(g):
                        cx = bx + 16 + c * 30
                        T.disc(f.d, (cx, ry + rh / 2), 12, MM_COLORS[code])
                    fx = bx + 16 + self.SLOTS * 30 + 14
                    for k in range(4):
                        kx = fx + (k % 2) * 13
                        ky = ry + rh / 2 - 7 + (k // 2) * 13
                        if k < ex:
                            T.disc(f.d, (kx, ky), 5, (240, 244, 250), shade=False)
                        elif k < ex + pa:
                            f.d.ellipse((kx - 5, ky - 5, kx + 5, ky + 5), outline=(200, 208, 224), width=2)
                        else:
                            T.disc(f.d, (kx, ky), 5, (44, 52, 70), shade=False)
                else:
                    for c in range(self.SLOTS):
                        cx = bx + 16 + c * 30
                        f.d.ellipse((cx - 12, ry + rh / 2 - 12, cx + 12, ry + rh / 2 + 12), fill=(30, 36, 50), outline=(48, 57, 78), width=1)
            if not self.done and s == self.turn_seat:
                pend = self.pending.get(s, [None] * self.SLOTS)
                py = y1 - 44
                f.text((bx, py - 16), "CURRENT", 11, T.DIM, bold=True)
                for c, code in enumerate(pend):
                    cx = bx + 16 + c * 30
                    if code is None:
                        f.d.ellipse((cx - 12, py + 6 - 12, cx + 12, py + 6 + 12), outline=(70, 82, 106), width=2)
                    else:
                        T.disc(f.d, (cx, py + 6), 12, MM_COLORS[code])


# =========================================================== HIGHER / LOWER 🔢
class GuessNumber(Game):
    key = "guessnumber"
    name = "Higher or Lower"
    tagline = "Zero in on the secret number"
    emoji = "🔢"
    rules = "The secret sits between 1 and 100. Take turns guessing; the frame tells you higher or lower. Ten guesses each, closest wins."
    TRIES = 10

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.secret = self.rng.randint(1, 100)
        self.history: list[list[int]] = [[] for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""
        self.low, self.high = 1, 100

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason)

    def status(self) -> str:
        if self.done:
            return self.reason
        return f"{self.pname(self.turn_seat)} · range {self.low}–{self.high}"

    def prompt(self) -> str:
        return "Tap Guess and send a number between 1 and 100."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        raw = action[1:] if action.startswith("g") else action
        if not re.fullmatch(r"\d{1,3}", raw.strip()):
            raise InvalidAction("Send a number.")
        n = int(raw)
        if not 1 <= n <= 100:
            raise InvalidAction("Between 1 and 100, please.")
        if any(n in h for h in self.history):
            raise InvalidAction("That number was already guessed.")
        self.history[seat].append(n)
        if n == self.secret:
            self.done, self.win_seat = True, seat
            self.reason = f"{self.pname(seat)} finds {self.secret}."
            return self.reason
        if n < self.secret:
            self.low = max(self.low, n + 1)
            hint = "higher"
        else:
            self.high = min(self.high, n - 1)
            hint = "lower"
        if all(len(h) >= self.TRIES for h in self.history):
            self.done = True
            best = min(range(len(self.players)), key=lambda i: min(abs(x - self.secret) for x in self.history[i]) if self.history[i] else 999)
            self.win_seat = best
            self.reason = f"No exact hit — {self.pname(best)} was closest to {self.secret}."
            return self.reason
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} guesses {n} — {hint}"

    def legal_actions(self, seat: int) -> list[str]:
        return []

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        lo, hi = self.low, self.high
        if difficulty >= 3:
            guess = (lo + hi) // 2
        else:
            guess = self.rng.randint(lo, hi)
        return f"g{guess}"

    def view(self, seat: int) -> ViewModel:
        modal = None
        if not self.done and seat == self.turn_seat:
            modal = ModalSpec("g", "Your guess", "Number from 1 to 100", f"{self.low}–{self.high}", "", 3, "Guess", "🎯", 0)
        return self._self_view(seat, modal=modal)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        track = (x0 + 40, y0 + 150, x1 - 40, y0 + 172)
        f.d.rounded_rectangle(track, radius=11, fill=(32, 38, 52))
        def pos(n):
            return track[0] + (track[2] - track[0]) * (n - 1) / 99
        f.d.rounded_rectangle((pos(self.low), track[1], pos(self.high), track[3]), radius=11, fill=(58, 72, 98))
        for i, p in enumerate(self.players):
            for n in self.history[i]:
                x = pos(n)
                y = track[1] - 16 if i == 0 else track[3] + 16
                T.disc(f.d, (x, y), 7, p.color, shade=False)
                f.d.line((x, y, x, track[1] if i else track[3]), fill=p.color, width=1)
        for n in (1, 25, 50, 75, 100):
            f.text((pos(n), track[3] + 26), str(n), 12, T.DIM, bold=True, anchor="ma")
        f.text((x0 + 40, y0 + 20), "SECRET BETWEEN", 13, T.DIM, bold=True)
        f.text((x0 + 40, y0 + 40), f"{self.low} — {self.high}", 54, T.TEXT, bold=True)
        if self.done:
            f.text((x1 - 40, y0 + 60), str(self.secret), 54, GOLD, bold=True, anchor="ra")
        for i, p in enumerate(self.players):
            f.text((x0 + 40 + i * 260, y1 - 26), f"{p.short(12)} · {' '.join(str(x) for x in self.history[i][-6:]) or '—'}", 14, p.color if i == self.turn_seat else T.DIM, bold=True)
