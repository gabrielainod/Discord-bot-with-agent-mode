"""Framework types shared by the engine, the renderer and every UI (Discord / web)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class InvalidAction(Exception):
    """Raised by a game when an action is not legal; the UI shows the message to the player."""


# --------------------------------------------------------------------- players
@dataclass
class Player:
    """A seat in a match.

    kind: "user"  -> a real Discord member
          "ai"    -> TripleTBot's own engine (named persona)
          "bot"   -> another Discord bot, played by an AI proxy wearing its name
    """

    index: int
    name: str
    user_id: Optional[int] = None
    kind: str = "user"
    avatar_url: Optional[str] = None
    avatar_bytes: Optional[bytes] = None
    difficulty: int = 2          # 1..4
    persona: str = "default"
    is_bot_player: bool = False  # True when the engine controls this seat

    @property
    def color(self):
        from ..render import theme

        return theme.SEAT_COLORS[self.index % len(theme.SEAT_COLORS)]

    @property
    def color_dark(self):
        from ..render import theme

        return theme.SEAT_COLORS_DARK[self.index % len(theme.SEAT_COLORS_DARK)]

    @property
    def label(self) -> str:
        return self.name

    @property
    def sub(self) -> str:
        if self.kind == "ai":
            return "TRIPLETBOT AI"
        if self.kind == "bot":
            return "BOT · AI PROXY"
        return "PLAYER"

    def short(self, n: int = 16) -> str:
        return self.name if len(self.name) <= n else self.name[: n - 1] + "…"


# -------------------------------------------------------------------- controls
@dataclass
class Control:
    """A tappable button. `id` is the action string sent back by the game."""

    id: str
    label: str = ""
    emoji: str = ""
    style: str = "secondary"     # primary | success | danger | secondary
    row: int = 0
    disabled: bool = False


@dataclass
class Option:
    id: str
    label: str
    emoji: str = ""
    description: str = ""


@dataclass
class Select:
    """A dropdown menu with at most 25 options."""

    placeholder: str
    options: list[Option]
    row: int = 0
    disabled: bool = False
    min_values: int = 1
    max_values: int = 1


@dataclass
class ModalSpec:
    """A pop-up text prompt (typing games). `id` is prefixed to the typed value."""

    id: str
    title: str
    label: str
    placeholder: str = ""
    value: str = ""
    max_length: int = 60
    button_label: str = "Type answer"
    button_emoji: str = "⌨️"
    row: int = 0
    style: str = "primary"
    disabled: bool = False


@dataclass
class ViewModel:
    buttons: list[Control] = field(default_factory=list)
    selects: list[Select] = field(default_factory=list)
    modal: Optional[ModalSpec] = None
    prompt: str = ""          # short "what now?" line, shown on the frame + embed
    open_modal_only: bool = False


# --------------------------------------------------------------------- results
@dataclass
class Result:
    winner: Optional[int]      # seat index, None for a draw
    reason: str = ""
    scores: Optional[list[float]] = None

    @property
    def draw(self) -> bool:
        return self.winner is None


# ------------------------------------------------------------------ match meta
@dataclass
class MatchMeta:
    game_name: str
    tagline: str
    round_no: int
    rounds: int
    code: str = ""
    mode: str = "PVP"


@dataclass
class LogEntry:
    text: str
    color: tuple = (147, 159, 182)
    icon: str = "•"
    seat: int = -1
