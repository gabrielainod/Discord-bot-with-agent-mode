"""Match engine: rounds, scoring, AI pulse and frame rendering.

Pure logic — no Discord imports. The Discord layer and the web simulator both
drive a ``Match`` the same way: act(), pulse() and render().
"""
from __future__ import annotations

import random
import string
import time
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from .types import InvalidAction, LogEntry, MatchMeta, Player, Result, ViewModel
from ..games import get
from ..games.base import Game
from ..render import theme as T
from ..render.frame import Frame

DRAW_POINTS = 0.5


def code4(rng: random.Random) -> str:
    return "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(4))


@dataclass
class Match:
    game_key: str
    players: list[Player]
    rounds: int = 3
    seed: Optional[int] = None
    channel_id: int = 0

    def __post_init__(self):
        self.rng = random.Random(self.seed if self.seed is not None else time.time_ns())
        self.scores = [0.0 for _ in self.players]
        self.round_no = 1
        self.log: list[LogEntry] = []
        self.settled = False
        self.finished = False
        self.match_winner: Optional[int] = None
        self.round_results: list[tuple[int, Optional[int], str]] = []
        self.ai_next: dict[int, float] = {}
        self.round_started_at = time.monotonic()
        self.settled_at: Optional[float] = None
        self.code = code4(self.rng)
        self.game_cls = get(self.game_key)
        if self.game_cls is None:
            raise ValueError(f"Unknown game: {self.game_key}")
        self.game: Game = self.game_cls(self.players, self.scores, self.rng, 1, self.rounds)
        self.log.append(LogEntry(f"Round 1 · {self.game.name} begins", (124, 92, 255), "◆"))

    # ------------------------------------------------------------------ meta
    @property
    def name(self) -> str:
        return self.game.name

    @property
    def mode(self) -> str:
        bots = [p for p in self.players if p.is_bot_player]
        if not bots:
            return "PVP"
        if any(p.kind == "bot" for p in bots):
            return "BOT DUEL"
        return "VS AI"

    @property
    def humans(self) -> list[Player]:
        return [p for p in self.players if not p.is_bot_player]

    def player_by_id(self, user_id: int) -> Optional[Player]:
        for p in self.players:
            if p.user_id == user_id:
                return p
        return None

    # ----------------------------------------------------------------- rules
    def acting(self) -> list[int]:
        if self.game.is_over():
            return []
        return self.game.acting()

    def can_act(self, seat: int) -> bool:
        return seat in self.acting()

    def ai_seats_pending(self) -> list[int]:
        return [s for s in self.acting() if self.players[s].is_bot_player]

    def needs_human(self) -> bool:
        return any(not self.players[s].is_bot_player for s in self.acting())

    # --------------------------------------------------------------- actions
    def act(self, seat: int, action: str) -> str:
        """Apply one action. Raises InvalidAction when it is not legal."""
        if self.finished:
            raise InvalidAction("This match is finished.")
        if self.settled:
            raise InvalidAction("The round is over — start the next one.")
        if seat not in self.acting():
            raise InvalidAction("Hold on, it is not your move.")
        msg = self.game.act(seat, action)
        if msg:
            self.log.append(LogEntry(msg, self.players[seat].color, "•"))
        self._settle()
        return msg

    def _settle(self) -> None:
        if self.settled or not self.game.is_over():
            return
        self.settled = True
        self.settled_at = time.monotonic()
        res: Result = self.game.result() or Result(None, "Round over")
        if res.winner is None:
            for i in range(len(self.players)):
                self.scores[i] += DRAW_POINTS
        else:
            self.scores[res.winner] += 1.0
        self.round_results.append((self.round_no, res.winner, res.reason))
        self.log.append(LogEntry(res.reason, (255, 199, 84), "★"))
        if self.round_no >= self.rounds:
            self.finished = True
            top = max(self.scores)
            winners = [i for i, s in enumerate(self.scores) if s == top]
            self.match_winner = winners[0] if len(winners) == 1 else None
            summary = "Match drawn" if self.match_winner is None else f"{self.players[self.match_winner].short(14)} wins the match"
            self.game.final_result = Result(self.match_winner, summary)
            self.log.append(LogEntry(summary, (34, 211, 238), "🏆"))

    def next_round(self) -> bool:
        if not self.settled or self.finished:
            return False
        self.round_no += 1
        self.settled = False
        self.settled_at = None
        self.ai_next.clear()
        self.game = self.game_cls(self.players, self.scores, self.rng, self.round_no, self.rounds)
        self.log.append(LogEntry(f"Round {self.round_no} · {self.game.name}", (124, 92, 255), "◆"))
        self.round_started_at = time.monotonic()
        return True

    # ------------------------------------------------------------------- AI
    def _ai_delay(self, seat: int) -> float:
        p = self.players[seat]
        game = self.game
        if getattr(game, "live", False) or game.timed:
            base = 0.9
        else:
            base = game.ai_delay()
        speed = {1: 1.35, 2: 1.0, 3: 0.8, 4: 0.62}.get(p.difficulty, 1.0)
        return base * speed * self.rng.uniform(0.75, 1.25)

    def pulse(self, now: Optional[float] = None) -> bool:
        """Advance timers and let bots play. Returns True when the frame changed."""
        now = now if now is not None else time.monotonic()
        changed = False
        if self.finished and self.game.is_over():
            return False
        try:
            if self.game.tick(now):
                changed = True
        except Exception:
            pass
        if not self.game.is_over():
            for seat in list(self.acting()):
                if not self.players[seat].is_bot_player:
                    continue
                due = self.ai_next.get(seat, 0.0)
                if now < due:
                    continue
                action = None
                try:
                    action = self.game.ai_action(seat, self.players[seat].difficulty)
                except Exception:
                    action = None
                if action is None:
                    self.ai_next[seat] = now + 0.35
                    continue
                try:
                    msg = self.game.act(seat, action)
                except InvalidAction:
                    self.ai_next[seat] = now + 0.4
                    continue
                except Exception:
                    self.ai_next[seat] = now + 0.6
                    continue
                if msg:
                    self.log.append(LogEntry(msg, self.players[seat].color, "•"))
                changed = True
                self.ai_next[seat] = now + self._ai_delay(seat)
        self._settle()
        return changed

    def ai_busy(self) -> bool:
        return bool(self.ai_seats_pending()) and not self.settled

    # --------------------------------------------------------------- rendered
    def meta(self) -> MatchMeta:
        return MatchMeta(
            game_name=self.game.name,
            tagline=self.game.tagline,
            round_no=self.round_no,
            rounds=self.rounds,
            code=f"{self.game.key[:3].upper()}-{self.code}",
            mode=self.mode,
        )

    def render(self, show_result: bool = True) -> Image.Image:
        frame = Frame(self.meta(), self.players, self.scores, self.log[-9:], accent=T.ACCENT, show_result=show_result)
        return frame.render(self.game)

    def view(self, seat: int) -> ViewModel:
        vm = self.game.view(seat)
        if not vm.prompt:
            vm.prompt = self.game.prompt()
        if self.settled:
            vm.buttons = []
            vm.selects = []
            vm.modal = None
        return vm

    def summary_line(self) -> str:
        return " · ".join(f"{p.short(12)} {self.scores[p.index]:g}" for p in self.players)
