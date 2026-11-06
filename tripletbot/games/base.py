"""Base class for every TripleTBot game.

A game is a pure, self-contained state machine plus a renderer. It never talks to
Discord: the same object drives the Discord UI and the browser simulator.

Contract
--------
* ``acting()``      seats allowed to play right now (empty when the game is over)
* ``act(seat, a)``  apply one action, return a short line for the live log
* ``legal_actions`` every action the seat may take (used by the AI)
* ``ai_action``     what the engine plays for a bot seat
* ``draw(frame)``   paint the board inside ``frame.board``
* ``view(seat)``    the controls that seat should see
"""
from __future__ import annotations

import copy
import random
from typing import Iterable, Optional

from ..core.types import Control, InvalidAction, ModalSpec, Option, Player, Result, Select, ViewModel


class Game:
    key: str = ""
    name: str = ""
    tagline: str = ""
    rules: str = ""
    min_players: int = 2
    max_players: int = 2
    simultaneous: bool = False     # every seat may act at once
    timed: bool = False            # the host ticks this game (countdowns)
    hidden_info: bool = False
    emoji: str = "🎮"

    def __init__(self, players: list[Player], scores: list[float], rng: random.Random, round_no: int = 1, rounds: int = 1):
        self.players = players
        self.scores = scores
        self.rng = rng
        self.round_no = round_no
        self.rounds = rounds
        self.names = [p.name for p in players]
        self.pending: dict[int, dict] = {}
        self.turn_seat: int = 0

    # ----------------------------------------------------------------- helpers
    def clone(self) -> "Game":
        return copy.deepcopy(self)

    def seat(self, i: int) -> Player:
        return self.players[i]

    def pname(self, i: int, n: int = 14) -> str:
        return self.players[i].short(n)

    def rng_pick(self, seq: Iterable):
        seq = list(seq)
        return self.rng.choice(seq) if seq else None

    def other(self, i: int) -> int:
        return (i + 1) % len(self.players)

    def opponents(self, i: int) -> list[int]:
        return [k for k in range(len(self.players)) if k != i]

    # ------------------------------------------------------------- game rules
    def status(self) -> str:
        return "Match in progress"

    def prompt(self) -> str:
        return ""

    def is_over(self) -> bool:
        raise NotImplementedError

    def result(self) -> Optional[Result]:
        return None

    def turn(self) -> int:
        return self.turn_seat

    def acting(self) -> list[int]:
        if self.is_over():
            return []
        t = self.turn()
        return [t] if t is not None and t >= 0 else []

    def can_act(self, seat: int) -> bool:
        return seat in self.acting()

    def act(self, seat: int, action: str) -> str:
        raise InvalidAction("This game has no actions.")

    def legal_actions(self, seat: int) -> list[str]:
        return []

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        acts = self.legal_actions(seat)
        return self.rng.choice(acts) if acts else None

    def ai_delay(self) -> float:
        return 1.15

    def tick(self, now: float) -> bool:
        """Advance timed state. Return True when the frame changed."""
        return False

    def view(self, seat: int) -> ViewModel:
        return ViewModel(prompt=self.prompt())

    def draw(self, f) -> None:
        raise NotImplementedError

    # --------------------------------------------------------------- ui sugar
    def _self_view(self, seat: int, buttons=None, selects=None, modal=None, prompt: str = "") -> ViewModel:
        locked = seat < 0 or not self.can_act(seat)
        btns = buttons or []
        sels = selects or []
        if locked:
            btns = [Control(b.id, b.label, b.emoji, b.style, b.row, True) for b in btns]
            sels = [Select(s.placeholder, s.options, s.row, True, s.min_values, s.max_values) for s in sels]
            if modal is not None:
                modal = ModalSpec(modal.id, modal.title, modal.label, modal.placeholder, modal.value,
                                  modal.max_length, modal.button_label, modal.button_emoji, modal.row, modal.style, True)
        return ViewModel(btns, sels, modal, prompt or self.prompt())

    @staticmethod
    def grid_buttons(actions: dict[str, tuple[str, str]], disabled_ids: Iterable[str] = (), rows: int = 5, per_row: int = 5) -> list[Control]:
        """actions: id -> (label, emoji). Laid out left-to-right, top-to-bottom."""
        out: list[Control] = []
        disabled = set(disabled_ids)
        for i, (aid, (label, emoji)) in enumerate(actions.items()):
            row = i // per_row
            if row >= rows:
                break
            out.append(Control(aid, label, emoji, "secondary", row, aid in disabled))
        return out

    # ------------------------------------------------------- coordinate picks
    def coord_selects(
        self,
        seat: int,
        rows: int,
        cols: int,
        row_labels=None,
        col_labels=None,
        row_placeholder: str = "Pick a row",
        col_placeholder: str = "Pick a column",
        skip_rows: bool = False,
    ) -> list[Select]:
        """Two dropdowns (row + column). The move fires once both are chosen."""
        p = self.pending.setdefault(seat, {})
        row_labels = row_labels or (lambda i: f"Row {i + 1}")
        col_labels = col_labels or (lambda i: f"Column {i + 1}")
        out: list[Select] = []
        if not skip_rows:
            opts = [Option(f"r:{i}", row_labels(i), "▫️") for i in range(rows)]
            out.append(Select(f"{row_placeholder}{' · ' + str(p['r'] + 1) if 'r' in p else ''}", opts, row=0))
        opts = [Option(f"c:{i}", col_labels(i), "▫️") for i in range(cols)]
        out.append(Select(f"{col_placeholder}{' · ' + str(p['c'] + 1) if 'c' in p else ''}", opts, row=1 if not skip_rows else 0))
        return out

    def coord_handle(self, seat: int, action: str):
        """Returns (row, col) when both halves are known, else None."""
        if action.startswith("p") and len(action) == 3 and action[1:].isdigit():
            return (int(action[1]), int(action[2]))
        kind, _, val = action.partition(":")
        if kind not in ("r", "c"):
            return None
        p = self.pending.setdefault(seat, {})
        try:
            p[kind] = int(val)
        except ValueError:
            return None
        if "r" in p and "c" in p:
            rc = (p["r"], p["c"])
            p.clear()
            return rc
        return None

    def par(self) -> str:
        """Score suffix for the sidebar, e.g. '3 – 2'."""
        return " · ".join(f"{self.pname(p.index, 8)} {self.scores[p.index]:g}" for p in self.players)
