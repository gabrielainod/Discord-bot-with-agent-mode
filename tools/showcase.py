"""Render every TripleTBot game to showcase/ (pure offline, no Discord needed).

    python -m tools.showcase            # all frames + contact sheet + replay gif
    python -m tools.showcase xox chess  # only those games
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tripletbot.core.match import Match
from tripletbot.core.types import Player
from tripletbot.games import CATALOG, keys
from tripletbot.render import theme as T

OUT = Path(__file__).resolve().parents[1] / "showcase"


def make_match(key: str, rounds: int = 3, seed: int = 42) -> Match:
    """Both seats are driven by the engine so a showcase frame always has content."""
    players = [
        Player(0, "Gabriel", kind="user", user_id=1, is_bot_player=True, difficulty=2),
        Player(1, "TripleTBot", kind="ai", difficulty=3, is_bot_player=True),
    ]
    return Match(key, players, rounds=rounds, seed=seed)


def play(match: Match, max_steps: int = 400):
    """Autoplay the engine until the round settles."""
    for step in range(max_steps):
        match.pulse(time.monotonic() + step * 1.0)
        if match.settled:
            break
    return match


def render_game(key: str, out: Path = OUT) -> Path:
    match = play(make_match(key))
    img = match.render(show_result=False)
    path = out / f"{key}.png"
    img.save(path)
    return path


def contact_sheet(paths: list[tuple[str, Path]], out: Path) -> Path:
    cols, rows = 4, 6
    tw, th, pad, cap = 400, 262, 10, 26
    w = cols * tw + (cols + 1) * pad
    h = rows * (th + cap) + (rows + 1) * pad
    sheet = Image.new("RGB", (w, h), (10, 12, 18))
    for i, (name, path) in enumerate(paths):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + cap + pad)
        thumb = Image.open(path).resize((tw, th), Image.LANCZOS)
        sheet.paste(thumb, (x, y))
        from PIL import ImageDraw

        d = ImageDraw.Draw(sheet)
        d.rectangle((x, y, x + tw - 1, y + th - 1), outline=(46, 54, 74), width=1)
        T.text(d, (x + 2, y + th + 5), name, 16, (200, 210, 226), bold=True)
    out_path = out / "contact-sheet.png"
    sheet.save(out_path)
    return out_path


def replay_gif(key: str = "connect4", out: Path = OUT) -> Path:
    """Capture every frame of a match and stitch a real animated replay."""
    match = make_match(key, rounds=1, seed=7)
    frames: list[Image.Image] = []
    steps = 0
    frames.append(match.render())
    while not match.finished and steps < 60:
        match.pulse(time.monotonic() + steps * 1.0)
        steps += 1
        if steps % 2 == 0:
            frames.append(match.render())
    if not frames:
        frames = [match.render()]
    small = [f.resize((640, 419), Image.LANCZOS) for f in frames]
    path = out / "replay.gif"
    small[0].save(path, save_all=True, append_images=small[1:], duration=650, loop=0, optimize=True)
    return path


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    wanted = [a for a in argv if a in keys()] or keys()
    rendered: list[tuple[str, Path]] = []
    for cls in CATALOG:
        if cls.key not in wanted:
            continue
        t0 = time.time()
        p = render_game(cls.key)
        rendered.append((cls.name, p))
        print(f"  {cls.name:24s} {time.time() - t0:5.2f}s -> {p.name}")
    if len(rendered) > 4:
        p = contact_sheet(rendered, OUT)
        print(f"  contact sheet -> {p}")
    p = replay_gif("connect4", OUT)
    print(f"  replay gif -> {p} ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
