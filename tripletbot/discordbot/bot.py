"""TripleTBot — the Discord layer.

One message per match: a rendered frame plus live components. The same Match
object renders for everyone in the channel, so spectators watch in real time.
"""
from __future__ import annotations

import asyncio
import io
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands

from ..core.match import Match
from ..core.stats import Stats
from ..core.types import Player
from ..games import CATALOG, get, resolve_choice
from ..render.catalog import catalog_poster
from .ui import MatchView, render_message

DIFFICULTIES = {
    1: "Easy",
    2: "Normal",
    3: "Hard",
    4: "Insane",
}
DIFF_CHOICES = [app_commands.Choice(name=f"{v} · {k}", value=k) for k, v in DIFFICULTIES.items()]

MAX_ROUNDS = 9


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text("utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def read_avatar(user) -> Optional[bytes]:
    try:
        return await user.display_avatar.with_size(128).read()
    except Exception:
        return None


@dataclass
class Session:
    """One live match living inside one channel."""

    bot: "TripleTBot"
    match: Match
    channel_id: int
    message: Optional[discord.Message] = None
    task: Optional[asyncio.Task] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    recorded: bool = False
    closed: bool = False
    last_touch: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        self.last_touch = time.monotonic()

    async def update(self) -> None:
        if self.message is None:
            return
        async with self.lock:
            try:
                embed, file = render_message(self.match)
                await self.message.edit(embed=embed, attachments=[file], view=MatchView(self))
            except discord.NotFound:
                self.closed = True
            except discord.HTTPException:
                pass
            except Exception as exc:  # pragma: no cover
                print(f"[TripleTBot] update failed: {exc!r}")


class TripleTBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.sessions: dict[int, Session] = {}
        self.stats = Stats()
        self.started_at = time.time()

    # ------------------------------------------------------------- lifecycle
    async def setup_hook(self) -> None:
        register_commands(self)
        guild_id = os.getenv("GUILD_ID")
        try:
            if guild_id:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            else:
                await self.tree.sync()
        except Exception as exc:  # pragma: no cover
            print(f"[TripleTBot] command sync failed: {exc!r}")

    async def on_ready(self) -> None:
        print(f"[TripleTBot] online as {self.user} · {len(CATALOG)} games ready")
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.playing, name="/play · 24 games · live boards"),
            )
        except Exception:
            pass

    # ---------------------------------------------------------------- matches
    def session_for(self, channel_id: int) -> Optional[Session]:
        s = self.sessions.get(channel_id)
        if s and not s.closed:
            return s
        return None

    async def build_players(self, interaction, vs, difficulty) -> list[Player]:
        host = interaction.user
        level = int(difficulty) if difficulty is not None else 2
        host_name = getattr(host, "display_name", None) or host.name
        p0 = Player(0, host_name, kind="user", user_id=host.id, avatar_bytes=await read_avatar(host))
        if vs is None:
            me = self.user
            p1 = Player(
                1,
                getattr(me, "display_name", None) or "TripleTBot",
                kind="ai",
                user_id=getattr(me, "id", None),
                difficulty=max(2, level),
                is_bot_player=True,
                avatar_bytes=await read_avatar(me) if me else None,
            )
        else:
            is_bot = bool(getattr(vs, "bot", False))
            p1 = Player(
                1,
                getattr(vs, "display_name", None) or vs.name,
                kind="bot" if is_bot else "user",
                user_id=vs.id,
                difficulty=level,
                is_bot_player=is_bot,
                avatar_bytes=await read_avatar(vs),
            )
        return [p0, p1]

    async def start_match(self, interaction, key: str, vs, rounds: int, difficulty) -> Optional[Session]:
        channel = interaction.channel
        existing = self.session_for(channel.id)
        if existing:
            await self.close_session(channel.id, quiet=True)
        players = await self.build_players(interaction, vs, difficulty)
        rounds = max(1, min(MAX_ROUNDS, int(rounds or 3)))
        match = Match(key, players, rounds=rounds, channel_id=channel.id)
        session = Session(self, match, channel.id)
        embed, file = render_message(match)
        message = await interaction.followup.send(embed=embed, file=file, view=MatchView(session), wait=True)
        session.message = message
        self.sessions[channel.id] = session
        session.task = asyncio.create_task(self._launch(session))
        return session

    async def _launch(self, session: Session) -> None:
        # small head start so the first frame is on screen before bots move
        await asyncio.sleep(1.2)
        await self._loop(session)

    async def _loop(self, session: Session) -> None:
        """The pulse: timers, bot moves, auto next-round, final score recording."""
        while not session.closed:
            await asyncio.sleep(0.75)
            match = session.match
            changed = False
            try:
                changed = match.pulse()
            except Exception as exc:  # pragma: no cover
                print(f"[TripleTBot] pulse error: {exc!r}")
            if match.settled and not match.finished and match.settled_at and time.monotonic() - match.settled_at > 5.0:
                if match.next_round():
                    changed = True
                    session.touch()
            if match.finished and not session.recorded:
                session.recorded = True
                try:
                    self.stats.record_match(match.players, match.match_winner, match.game_key)
                except Exception:
                    pass
            if changed:
                await session.update()
            if match.finished and match.settled_at and time.monotonic() - match.settled_at > 900:
                break
            if time.monotonic() - session.last_touch > 3600:
                break
        session.closed = True
        if self.sessions.get(session.channel_id) is session:
            self.sessions.pop(session.channel_id, None)

    async def rematch(self, session: Session, interaction: discord.Interaction) -> None:
        old = session.match
        session.match = Match(old.game_key, old.players, rounds=old.rounds, channel_id=session.channel_id)
        session.recorded = False
        session.touch()
        await interaction.response.defer()
        await session.update()
        if session.task is None or session.task.done():
            session.closed = False
            session.task = asyncio.create_task(self._loop(session))

    async def close_session(self, channel_id: int, quiet: bool = False) -> bool:
        session = self.sessions.pop(channel_id, None)
        if not session:
            return False
        session.closed = True
        if session.task and not session.task.done():
            session.task.cancel()
        if not quiet and session.message:
            try:
                embed = discord.Embed(
                    title="Match cancelled",
                    description="The board is closed. Start a new one with `/play`.",
                    color=0x6B7280,
                )
                embed.set_image(url="attachment://triplettbot.png")
                await session.message.edit(embed=embed, view=None, attachments=[])
            except Exception:
                pass
        return True


# --------------------------------------------------------------------- commands
async def game_autocomplete(interaction: discord.Interaction, current: str):
    cur = (current or "").lower()
    out = []
    for cls in CATALOG:
        if cur in cls.name.lower() or cur in cls.key or not cur:
            out.append(app_commands.Choice(name=f"{cls.name} · {cls.tagline}"[:100], value=cls.key))
    return out[:25]


def register_commands(bot: TripleTBot) -> None:
    tree = bot.tree
    tree.clear_commands(guild=None)

    async def begin(interaction: discord.Interaction, key: str, vs: Optional[discord.Member], rounds: int, difficulty) -> None:
        if vs is not None and vs.id == interaction.user.id:
            await interaction.response.send_message("You cannot challenge yourself — pick a rival.", ephemeral=True)
            return
        if interaction.channel is None:
            await interaction.response.send_message("Use this in a server channel.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        try:
            await bot.start_match(interaction, key, vs, rounds, difficulty)
        except Exception as exc:
            await interaction.followup.send(f"Could not start the match: {exc}", ephemeral=True)

    # ---- /play -------------------------------------------------------------
    @tree.command(name="play", description="Start any TripleTBot game — a live visual board for the whole channel")
    @app_commands.describe(
        game="Which game to play",
        vs="Rival: leave empty to face TripleTBot, or pick a member/bot in this server",
        rounds="Rounds in the match (1-9)",
        difficulty="Bot strength when an AI is on the board",
    )
    @app_commands.autocomplete(game=game_autocomplete)
    @app_commands.choices(difficulty=DIFF_CHOICES)
    async def play(
        interaction: discord.Interaction,
        game: str,
        vs: Optional[discord.Member] = None,
        rounds: int = 3,
        difficulty: Optional[int] = None,
    ):
        cls = resolve_choice(game)
        if cls is None:
            await interaction.response.send_message("Unknown game — check `/games` for the full list.", ephemeral=True)
            return
        await begin(interaction, cls.key, vs, rounds, difficulty)

    # ---- one command per game ---------------------------------------------
    for cls in CATALOG:
        def make(cls=cls):
            @app_commands.command(name=cls.key, description=f"{cls.name} · {cls.tagline}"[:100])
            @app_commands.describe(
                vs="Rival: empty = TripleTBot AI, or pick a member/bot",
                rounds="Rounds in the match (1-9)",
                difficulty="Bot strength",
            )
            @app_commands.choices(difficulty=DIFF_CHOICES)
            async def _cmd(
                interaction: discord.Interaction,
                vs: Optional[discord.Member] = None,
                rounds: int = 3,
                difficulty: Optional[int] = None,
            ):
                await begin(interaction, cls.key, vs, rounds, difficulty)

            _cmd.__name__ = f"cmd_{cls.key}"
            return _cmd

        tree.add_command(make())

    # ---- /games ------------------------------------------------------------
    @tree.command(name="games", description="Poster with all 24 TripleTBot games")
    async def games(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        buf = io.BytesIO()
        catalog_poster().save(buf, "PNG", optimize=True)
        buf.seek(0)
        embed = discord.Embed(
            title=f"TripleTBot Arcade · {len(CATALOG)} games",
            description="Every title renders a live board image and updates after each move.\n"
            "Play 1v1 against a member, against TripleTBot's engine, or challenge another bot in the server.",
            color=0x7C5CFF,
        )
        groups = {
            "Board": ["xox", "connect4", "reversi", "checkers", "chess", "ultimate_xox", "dots_boxes", "nim"],
            "Grid": ["battleship", "minesweeper", "memory", "game2048", "snakes"],
            "Brain": ["hangman", "wordle", "scramble", "trivia", "mastermind", "mathduel", "guessnumber"],
            "Arcade": ["typefast", "reaction", "simon", "rps"],
        }
        for label, keys in groups.items():
            names = ", ".join(f"`/{k}`" for k in keys if k in {c.key for c in CATALOG})
            embed.add_field(name=label, value=names, inline=False)
        embed.set_footer(text="/play <game> vs:@rival rounds:3 difficulty:Hard")
        embed.set_image(url="attachment://games.png")
        await interaction.followup.send(embed=embed, file=discord.File(buf, filename="games.png"))

    # ---- /rules ------------------------------------------------------------
    @tree.command(name="rules", description="How to play a specific game")
    @app_commands.describe(game="Which game")
    @app_commands.autocomplete(game=game_autocomplete)
    async def rules(interaction: discord.Interaction, game: str):
        cls = resolve_choice(game)
        if cls is None:
            await interaction.response.send_message("Unknown game — try `/games`.", ephemeral=True)
            return
        seats = "1v1" if cls.max_players <= 2 else f"2 to {cls.max_players} players"
        embed = discord.Embed(title=f"{cls.name} · {cls.tagline}", description=cls.rules, color=0x7C5CFF)
        embed.add_field(name="Players", value=seats, inline=True)
        embed.add_field(name="Beats AI?", value="Yes — 4 difficulty levels", inline=True)
        embed.add_field(name="Command", value=f"`/{cls.key} vs:@rival rounds:3`", inline=False)
        if cls.simultaneous:
            embed.add_field(name="Note", value="Simultaneous game: everyone can act at once.", inline=False)
        if cls.timed:
            embed.add_field(name="Note", value="Timed game: the clock runs from the first frame.", inline=False)
        await interaction.response.send_message(embed=embed)

    # ---- /stats + /leaderboard --------------------------------------------
    @tree.command(name="stats", description="Your TripleTBot record")
    @app_commands.describe(user="Check someone else (optional)")
    async def stats(interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        data = bot.stats.user(target.id, getattr(target, "display_name", target.name))
        played = data["wins"] + data["losses"] + data["draws"]
        rate = (data["wins"] / played * 100) if played else 0.0
        embed = discord.Embed(title=f"{data['name']}'s record", color=0x7C5CFF)
        embed.add_field(name="Wins", value=str(data["wins"]), inline=True)
        embed.add_field(name="Losses", value=str(data["losses"]), inline=True)
        embed.add_field(name="Draws", value=str(data["draws"]), inline=True)
        embed.add_field(name="Win rate", value=f"{rate:.0f}%", inline=True)
        embed.add_field(name="Best streak", value=str(data.get("best_streak", 0)), inline=True)
        embed.add_field(name="XP", value=str(data.get("xp", 0)), inline=True)
        top_games = sorted(data.get("games", {}).items(), key=lambda kv: -kv[1].get("w", 0))[:5]
        if top_games:
            lines = []
            for key, rec in top_games:
                cls = get(key)
                name = cls.name if cls else key
                lines.append(f"**{name}** — {rec.get('w', 0)}W / {rec.get('l', 0)}L")
            embed.add_field(name="Favourite boards", value="\n".join(lines), inline=False)
        if not played:
            embed.set_footer(text="No matches yet — /play to start one")
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @tree.command(name="leaderboard", description="Top TripleTBot players in this server")
    async def leaderboard(interaction: discord.Interaction):
        rows = bot.stats.top(10)
        env = discord.Embed(title="TripleTBot leaderboard", color=0x7C5CFF)
        if not rows:
            env.description = "Nobody has played yet. Be the first — `/play`."
        else:
            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for i, (name, rec) in enumerate(rows):
                badge = medals[i] if i < 3 else f"`{i + 1}.`"
                lines.append(f"{badge} **{name}** — {rec['wins']}W / {rec['losses']}L / {rec['draws']}D")
            env.description = "\n".join(lines)
        totals = bot.stats.totals()
        env.set_footer(text=f"{totals['matches']} matches played · {totals['players']} tracked players")
        await interaction.response.send_message(embed=env)

    # ---- /cancel + /help ---------------------------------------------------
    @tree.command(name="cancel", description="Cancel the match running in this channel")
    async def cancel(interaction: discord.Interaction):
        session = bot.session_for(interaction.channel.id)
        if not session:
            await interaction.response.send_message("There is no match running here.", ephemeral=True)
            return
        host = session.match.players[0]
        if interaction.user.id != host.user_id and not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Only the host or a moderator can cancel this match.", ephemeral=True)
            return
        await interaction.response.defer()
        await bot.close_session(interaction.channel.id)

    @tree.command(name="tripletbot", description="What TripleTBot can do")
    async def help_cmd(interaction: discord.Interaction):
        embed = discord.Embed(
            title="TripleTBot — 24 games, zero walls of text",
            description=(
                "Every match is a rendered board that updates live, so the whole channel watches every move.\n\n"
                "**Start a match**\n`/play game:xox vs:@rival rounds:3 difficulty:Hard`\n"
                "Leave `vs` empty to face the engine, or mention a member — including another bot.\n\n"
                "**Every game also has its own command**\n`/xox` `/chess` `/typefast` `/hangman` …\n\n"
                "**Other commands**\n`/games` · `/rules` · `/stats` · `/leaderboard` · `/cancel`"
            ),
            color=0x7C5CFF,
        )
        embed.add_field(
            name="Play against other bots",
            value="Discord bots cannot press buttons, so when you challenge a bot TripleTBot runs an AI proxy wearing that bot's name and avatar.",
            inline=False,
        )
        embed.set_footer(text=f"Online · {len(CATALOG)} games · v1.0")
        await interaction.response.send_message(embed=embed)


def run() -> None:
    load_env()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "DISCORD_TOKEN is missing.\n"
            "  1. Create an application at https://discord.com/developers/applications\n"
            "  2. Bot → Reset Token, copy it\n"
            "  3. Put DISCORD_TOKEN=your_token in .env (or export it)\n"
            "  4. Invite the bot with the 'bot' + 'applications.commands' scopes"
        )
    bot = TripleTBot()
    bot.run(token, log_handler=None)
