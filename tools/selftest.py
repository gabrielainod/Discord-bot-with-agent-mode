"""Self-check: every game must play a complete AI match, render and build a UI.

    python tools/selftest.py            # all games
    python tools/selftest.py chess xox  # subset
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tripletbot.core.match import Match
from tripletbot.core.types import Player
from tripletbot.games import CATALOG, keys


def run_game(key: str, difficulty: int = 3, rounds: int = 1, seed: int = 5):
    players = [
        Player(0, "Selftest A", kind="ai", is_bot_player=True, difficulty=difficulty),
        Player(1, "Selftest B", kind="ai", is_bot_player=True, difficulty=max(1, difficulty - 1)),
    ]
    match = Match(key, players, rounds=rounds, seed=seed)
    match.render()                                    # frame at kickoff
    steps = 0
    while not match.finished and steps < 800:
        match.pulse(time.monotonic() + steps * 1.0)
        steps += 1
        if match.settled and not match.finished:
            match.next_round()
    if not match.finished:
        raise AssertionError(f"match did not finish after {steps} pulses")
    img = match.render()
    assert img.size == (1100, 720), img.size
    vm = match.view(0)
    assert vm is not None
    # every remaining round must be startable and renderable
    return steps, match.round_results[-1][2] if match.round_results else ""


def discord_view(key: str) -> None:
    from tripletbot.discordbot.ui import MatchView, render_message

    players = [
        Player(0, "Gabriel", kind="user", user_id=1),
        Player(1, "TripleTBot", kind="ai", is_bot_player=True, user_id=2, difficulty=2),
    ]
    match = Match(key, players, rounds=3, seed=9)
    for i in range(3):
        match.pulse(time.monotonic() + i)
    embed, file = render_message(match)
    assert file.filename.endswith(".png")

    class S:
        def __init__(self, m):
            self.match = m
            self.bot = None
            self.channel_id = 0
            self.message = None

    view = MatchView(S(match))
    assert len(view.children) <= 25, f"{key}: {len(view.children)} components"


def main(argv: list[str]) -> int:
    wanted = [a for a in argv if a in keys()] or keys()
    failures = 0
    print(f"{'game':22s} {'steps':>6s} {'render':>8s} {'discord':>8s}  result")
    for cls in CATALOG:
        if cls.key not in wanted:
            continue
        t0 = time.time()
        try:
            steps, result = run_game(cls.key)
        except Exception:
            failures += 1
            print(f"{cls.key:22s} {'-':>6s} {'FAIL':>8s} {'-':>8s}  {traceback.format_exc().splitlines()[-1]}")
            continue
        render_ms = int((time.time() - t0) * 1000)
        try:
            discord_view(cls.key)
            dview = "ok"
        except Exception:
            dview = "FAIL"
            failures += 1
        print(f"{cls.key:22s} {steps:6d} {render_ms:7d}ms {dview:>8s}  {result[:48]}")
    total = len(wanted)
    print(f"\n{total - failures}/{total} games healthy")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
