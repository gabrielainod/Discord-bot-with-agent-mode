"""Tiny JSON player-stats store (wins, losses, draws, per-game record, streaks)."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

DEFAULT_PATH = Path(os.environ.get("TRIPLETBOT_STATS", "data/stats.json"))


class Stats:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {"users": {}, "matches": 0, "since": time.time()}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text("utf-8"))
            except Exception:
                pass
        self._data.setdefault("users", {})
        self._data.setdefault("matches", 0)

    def _save(self) -> None:
        try:
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=1)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def user(self, user_id: int, name: str = "player") -> dict:
        key = str(user_id)
        u = self._data["users"].setdefault(
            key,
            {"name": name, "wins": 0, "losses": 0, "draws": 0, "games": {}, "streaka": 0, "best_streak": 0, "xp": 0},
        )
        u["name"] = name
        u.setdefault("games", {})
        return u

    def record_match(self, players: list, winner: Optional[int], game_key: str) -> None:
        """players: list of objects with .user_id and .name and .is_bot_player."""
        self._data["matches"] = self._data.get("matches", 0) + 1
        for i, p in enumerate(players):
            if getattr(p, "is_bot_player", False) or not p.user_id:
                continue
            u = self.user(p.user_id, p.name)
            g = u["games"].setdefault(game_key, {"w": 0, "l": 0, "d": 0})
            if winner is None:
                u["draws"] += 1
                g["d"] += 1
                u["streak"] = 0
                u["xp"] += 10
            elif winner == i:
                u["wins"] += 1
                g["w"] += 1
                u["streak"] = u.get("streak", 0) + 1
                u["best_streak"] = max(u.get("best_streak", 0), u["streak"])
                u["xp"] += 35
            else:
                u["losses"] += 1
                g["l"] += 1
                u["streak"] = 0
                u["xp"] += 8
        self._save()

    def top(self, limit: int = 10) -> list[tuple[str, dict]]:
        users = [(v.get("name", k), v) for k, v in self._data["users"].items()]
        users.sort(key=lambda kv: (-kv[1].get("wins", 0), kv[1].get("losses", 0)))
        return users[:limit]

    def totals(self) -> dict:
        return {"matches": self._data.get("matches", 0), "players": len(self._data["users"])}
