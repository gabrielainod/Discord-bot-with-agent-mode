"""TripleTBot's game engine: negamax with alpha-beta pruning + personas.

Games that are small enough implement ``legal_actions`` / ``act`` / ``result`` on
clones, which lets them borrow the generic search below. Bigger games plug in
their own evaluation function.
"""
from __future__ import annotations

import random
from typing import Callable, Optional

INF = float("inf")

DIFFICULTIES = {1: "Easy", 2: "Normal", 3: "Hard", 4: "Insane"}

# How often a bot simply plays a random (non-optimal) move, and how deep it looks.
PROFILE = {
    1: dict(depth=0, blunder=0.55, label="Easy"),
    2: dict(depth=2, blunder=0.22, label="Normal"),
    3: dict(depth=4, blunder=0.06, label="Hard"),
    4: dict(depth=9, blunder=0.0, label="Insane"),
}

# Named personas: they change the trash-talk line, not the raw strength.
PERSONAS = {
    "default": dict(name="TripleT", blurb="The house engine"),
    "nova": dict(name="Nova", blurb="Calm, positional, ruthless"),
    "byte": dict(name="Byte", blurb="Chaotic and fast"),
    "vex": dict(name="Vex", blurb="Loves a trap"),
}


def depth_for(difficulty: int) -> int:
    return PROFILE.get(difficulty, PROFILE[2])["depth"]


def blunder_for(difficulty: int) -> float:
    return PROFILE.get(difficulty, PROFILE[2])["blunder"]


def negamax(game, seat: int, depth: int, alpha: float, beta: float, evaluate: Callable, deadline: Optional[float] = None, nodes: Optional[list] = None) -> float:
    if nodes is not None:
        nodes[0] += 1
        if deadline is not None and nodes[0] % 64 == 0:
            import time

            if time.monotonic() > deadline:
                raise TimeoutError
    res = game.result()
    if res is not None:
        if res.winner is None:
            return 0.0
        return 1_000_000.0 if res.winner == seat else -1_000_000.0
    if depth <= 0:
        return float(evaluate(game, seat))
    turn = game.turn()
    children = game.legal_actions(turn)
    if not children:
        return float(evaluate(game, seat))
    best = -INF
    for a in children:
        child = game.clone()
        child.act(turn, a)
        val = -negamax(child, turn, depth - 1, -beta, -alpha, evaluate, deadline, nodes)
        if val > best:
            best = val
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def best_move(game, seat: int, depth: int, evaluate: Callable, rng: random.Random, blunder: float = 0.0, time_budget: float = 2.5) -> Optional[str]:
    acts = game.legal_actions(seat)
    if not acts:
        return None
    if depth <= 0 or rng.random() < blunder:
        return rng.choice(acts)
    # Cheap move ordering: give captures / centre moves a first look.
    ordered = list(acts)
    rng.shuffle(ordered)
    if hasattr(game, "move_priority"):
        try:
            ordered.sort(key=lambda a: -game.move_priority(seat, a))
        except Exception:
            pass
    import time

    deadline = time.monotonic() + time_budget
    best_a = ordered[0]
    best_v = -INF
    alpha = -INF
    for a in ordered:
        child = game.clone()
        child.act(seat, a)
        opp = child.turn() if child.turn() >= 0 else (1 - seat)
        try:
            v = -negamax(child, opp, depth - 1, -INF, -alpha, evaluate, deadline, [0])
        except TimeoutError:
            break
        if v > best_v:
            best_v, best_a = v, a
        alpha = max(alpha, v)
    return best_a


def trash_talk(difficulty: int, rng: random.Random, persona: str = "default") -> str:
    lines = {
        1: ["Good luck, have fun!", "I'm still warming up.", "Take your time."],
        2: ["Let's see what you've got.", "Nice one.", "Not bad at all."],
        3: ["You walked into that.", "Calculated.", "That was the plan."],
        4: ["This board is already mine.", "Resistance is inefficient.", "I solved it three moves ago."],
    }
    return rng.choice(lines.get(difficulty, lines[2]))
