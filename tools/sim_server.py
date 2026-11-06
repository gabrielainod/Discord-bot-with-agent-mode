"""Playable TripleTBot simulator — no Discord token required.

    python tools/sim_server.py            # http://0.0.0.0:8000

It serves the exact same engine and frames the Discord bot posts, wrapped in a
phone-sized Discord-style UI, so the games can be tested (and demoed) anywhere.
"""
from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tripletbot.core.match import Match
from tripletbot.core.types import InvalidAction, Player, ViewModel
from tripletbot.games import CATALOG, get

INDEX = ROOT / "tripletbot" / "web" / "index.html"
MATCHES: dict[str, "Sim"] = {}
LOCK = threading.Lock()


def hexc(color) -> str:
    return "#%02x%02x%02x" % tuple(int(c) for c in color[:3])


class Sim:
    def __init__(self, key: str, mode: str = "solo", rounds: int = 3, difficulty: int = 2):
        self.id = uuid.uuid4().hex[:10]
        self.key = key
        self.mode = mode
        self.version = 0
        self.lock = threading.Lock()
        self.png: bytes | None = None
        self.png_version = -1
        self.created = time.time()
        human = mode != "watch"
        players = [
            Player(0, "You" if human else "TripleTBot I", kind="user", user_id=1,
                   is_bot_player=not human, difficulty=difficulty),
            Player(1, "TripleTBot", kind="ai", user_id=2, is_bot_player=True, difficulty=difficulty),
        ]
        self.match = Match(key, players, rounds=max(1, min(9, rounds)))

    # ------------------------------------------------------------------ engine
    def pulse(self) -> bool:
        m = self.match
        changed = m.pulse()
        if m.settled and not m.finished and m.settled_at and time.monotonic() - m.settled_at > 3.2:
            if m.next_round():
                changed = True
        if changed:
            self.version += 1
        return changed

    def act(self, action: str):
        m = self.match
        if m.finished:
            return "This match is finished — start a new one."
        if m.settled:
            return "The round is over — the next one starts in a moment."
        if self.mode == "watch":
            return "AI vs AI — just watch, or start your own match."
        if 0 not in m.acting():
            return "Hold on — the engine is playing."
        try:
            m.act(0, action)
        except InvalidAction as exc:
            return str(exc)
        except Exception as exc:  # pragma: no cover
            return f"Move rejected ({exc})."
        self.version += 1
        return None

    def image(self) -> bytes:
        if self.png is None or self.png_version != self.version:
            img = self.match.render()
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            self.png = buf.getvalue()
            self.png_version = self.version
        return self.png

    def state(self) -> dict:
        with self.lock:
            self.pulse()
            m = self.match
            seat = (m.acting() or [0])[0]
            vm = ViewModel()
            if not m.settled:
                try:
                    vm = m.game.view(seat)
                except Exception:
                    vm = ViewModel()
            locked = m.settled or m.players[seat].is_bot_player
            buttons = [
                dict(id=c.id, label=c.label, emoji=c.emoji, row=max(0, min(4, c.row)),
                     style=c.style, disabled=bool(c.disabled or locked))
                for c in vm.buttons
            ]
            selects = [
                dict(placeholder=s.placeholder, row=s.row, disabled=bool(s.disabled or locked),
                     options=[dict(id=o.id, label=o.label, emoji=o.emoji) for o in s.options][:25])
                for s in vm.selects
            ]
            modal = None
            if vm.modal is not None and not locked:
                modal = dict(id=vm.modal.id, title=vm.modal.title, label=vm.modal.label,
                             placeholder=vm.modal.placeholder, max_length=vm.modal.max_length)
            return dict(
                id=self.id,
                version=self.version,
                image=f"/img/{self.id}.png?v={self.version}",
                title=f"{m.game.name} · round {m.round_no}/{m.rounds}",
                status=m.game.status(),
                prompt=vm.prompt or m.game.prompt(),
                round=m.round_no,
                rounds=m.rounds,
                mode=self.mode,
                settled=m.settled,
                finished=m.finished,
                buttons=buttons,
                selects=selects,
                modal=modal,
                scores=[
                    dict(name=p.short(14), score=f"{m.scores[p.index]:g}", color=hexc(p.color), kind=p.kind)
                    for p in m.players
                ],
            )


def prune() -> None:
    now = time.time()
    with LOCK:
        dead = [k for k, s in MATCHES.items() if now - s.created > 3600]
        for k in dead[:40]:
            MATCHES.pop(k, None)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "TripleTBotSim/1.0"

    def log_message(self, fmt, *args):  # keep the console readable
        pass

    # ------------------------------------------------------------------ output
    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, payload, code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"))

    # -------------------------------------------------------------------- GET
    def do_GET(self) -> None:
        url = urlparse(self.path)
        q = parse_qs(url.query)
        path = url.path
        try:
            if path in ("/", "/index.html"):
                self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            elif path == "/healthz":
                self._send(200, b"ok", "text/plain")
            elif path == "/api/games":
                self._json([
                    dict(key=c.key, name=c.name, tagline=c.tagline, rules=c.rules,
                         seats=c.max_players, simultaneous=c.simultaneous, timed=c.timed)
                    for c in CATALOG
                ])
            elif path == "/api/new":
                key = (q.get("game") or ["xox"])[0]
                if get(key) is None:
                    self._json({"error": "unknown game"}, 404)
                    return
                mode = (q.get("mode") or ["solo"])[0]
                rounds = int((q.get("rounds") or ["3"])[0])
                difficulty = int((q.get("difficulty") or ["2"])[0])
                sim = Sim(key, mode, rounds, difficulty)
                with LOCK:
                    MATCHES[sim.id] = sim
                prune()
                self._json(sim.state())
            elif path == "/api/state":
                mid = (q.get("id") or [""])[0]
                sim = MATCHES.get(mid)
                if not sim:
                    self._json({"error": "match not found"}, 404)
                    return
                self._json(sim.state())
            elif path.startswith("/img/"):
                mid = path[5:].split(".")[0]
                sim = MATCHES.get(mid)
                if not sim:
                    self._send(404, b"no match", "text/plain")
                    return
                with sim.lock:
                    data = sim.image()
                self._send(200, data, "image/png")
            else:
                self._send(404, b"not found", "text/plain")
        except Exception as exc:  # pragma: no cover
            self._json({"error": repr(exc)}, 500)

    # ------------------------------------------------------------------- POST
    def do_POST(self) -> None:
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}
        try:
            if url.path == "/api/act":
                sim = MATCHES.get(body.get("id", ""))
                if not sim:
                    self._json({"error": "match not found"}, 404)
                    return
                err = sim.act(str(body.get("action", "")))
                payload = sim.state()
                if err:
                    payload["error"] = err
                self._json(payload)
            else:
                self._json({"error": "not found"}, 404)
        except Exception as exc:  # pragma: no cover
            self._json({"error": repr(exc)}, 500)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    print(f"TripleTBot simulator on http://{host}:{port} · {len(CATALOG)} games")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
