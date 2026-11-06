"""Game registry for TripleTBot."""
from __future__ import annotations

from typing import Optional

from .arcade import GuessNumber, Mastermind, MathDuel, Reaction, RPS, Simon, TypeFast
from .base import Game
from .board import Connect4, Reversi, UltimateXox, Xox
from .board2 import DotsBoxes, Memory, Nim, SnakesLadders
from .grid import Battleship, Game2048, Minesweeper
from .strategy import Checkers, Chess
from .words import Hangman, Scramble, Trivia, Wordle

# Display order for /games and the picker.
CATALOG: list[type[Game]] = [
    # turn-based board games
    Xox, Connect4, Reversi, Checkers, Chess, UltimateXox, DotsBoxes, Nim,
    # puzzle / grid duels
    Battleship, Minesweeper, Memory, Game2048, SnakesLadders,
    # word & brain
    Hangman, Wordle, Scramble, Trivia, Mastermind, MathDuel, GuessNumber,
    # arcade
    TypeFast, Reaction, Simon, RPS,
]

GAMES: dict[str, type[Game]] = {cls.key: cls for cls in CATALOG}


def get(key: str) -> Optional[type[Game]]:
    return GAMES.get(key)


def all_games() -> list[type[Game]]:
    return list(CATALOG)


def names() -> list[str]:
    return [cls.name for cls in CATALOG]


def keys() -> list[str]:
    return [cls.key for cls in CATALOG]


def _norm(s: str) -> str:
    return s.strip().lower().replace("_", " ").replace("-", " ")


def resolve_choice(value: str) -> Optional[type[Game]]:
    """Accept a key ("xox"), a display name ("Tic-Tac-Toe") or an unambiguous prefix."""
    v = _norm(value)
    if v in GAMES:
        return GAMES[v]
    for cls in CATALOG:
        if _norm(cls.name) == v or _norm(cls.key) == v:
            return cls
    matches = [cls for cls in CATALOG if v and (v in _norm(cls.key) or v in _norm(cls.name))]
    return matches[0] if len(matches) == 1 else None
