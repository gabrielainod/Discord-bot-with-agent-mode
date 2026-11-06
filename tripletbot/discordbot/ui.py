"""Discord components: one live message per match, rebuilt from the game ViewModel."""
from __future__ import annotations

import io
import discord

from ..core.match import Match
from ..core.types import Control, InvalidAction, Select, ViewModel

IMG = "triplettbot.png"
ACCENT = 0x7C5CFF

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
    "secondary": discord.ButtonStyle.secondary,
}


def render_message(match: Match) -> tuple[discord.Embed, discord.File]:
    img = match.render()
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    file = discord.File(buf, filename=IMG)

    game = match.game
    embed = discord.Embed(
        title=f"{game.name} · round {match.round_no}/{match.rounds}",
        description=f"**{game.status()}**",
        color=ACCENT,
    )
    for p in match.players:
        tag = "🤖" if p.kind == "ai" else ("🛰️" if p.kind == "bot" else "🎮")
        embed.add_field(name=f"{tag} {p.name}", value=f"{match.scores[p.index]:g} wins", inline=True)
    prompt = game.prompt()
    if prompt and not match.finished:
        embed.add_field(name="How to play", value=prompt, inline=False)
    if match.settled and not match.finished:
        embed.add_field(name="Next round", value="Starting automatically in a few seconds…", inline=False)
    footer = "TripleTBot Arcade · the board above updates live for everyone"
    if match.finished:
        footer = "Match finished · /play for a rematch, /stats for the record"
    embed.set_footer(text=footer)
    embed.set_image(url=f"attachment://{IMG}")
    return embed, file


class MatchView(discord.ui.View):
    """Every interaction funnels through ``handle`` so seats are enforced server-side."""

    def __init__(self, session):
        super().__init__(timeout=None)
        self.session = session
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        match: Match = self.session.match
        if match.settled:
            if match.finished:
                btn = discord.ui.Button(label="Rematch", emoji="🔁", style=discord.ButtonStyle.primary, row=0)
                btn.callback = self._rematch
                self.add_item(btn)
            else:
                btn = discord.ui.Button(label="Next round now", emoji="▶️", style=discord.ButtonStyle.primary, row=0)
                btn.callback = self._next_round
                self.add_item(btn)
            return

        acting = match.acting()
        seat = acting[0] if acting else 0
        try:
            vm: ViewModel = match.game.view(seat)
        except Exception:
            vm = ViewModel()
        locked = match.players[seat].is_bot_player
        for c in vm.buttons:
            self.add_item(GameButton(self, c, locked))
        for s in vm.selects:
            self.add_item(GameSelect(self, s, locked))
        if vm.modal is not None:
            self.add_item(ModalButton(self, vm.modal, locked))

    # --------------------------------------------------------------- handlers
    async def handle(self, interaction: discord.Interaction, action: str) -> None:
        match: Match = self.session.match
        player = match.player_by_id(interaction.user.id)
        if player is None:
            await interaction.response.send_message(
                "You are spectating this match — start your own with `/play`.", ephemeral=True
            )
            return
        if player.index not in match.acting():
            who = match.players[match.acting()[0]].name if match.acting() else "nobody"
            await interaction.response.send_message(f"Wait for your turn — it is **{who}** right now.", ephemeral=True)
            return
        try:
            match.act(player.index, action)
        except InvalidAction as exc:
            await interaction.response.send_message(f"⛔ {exc}", ephemeral=True)
            return
        except Exception as exc:  # never let a bad click kill the match
            await interaction.response.send_message(f"⛔ That move was rejected ({exc}).", ephemeral=True)
            return
        self.session.touch()
        await interaction.response.defer()
        await self.session.update()

    async def _next_round(self, interaction: discord.Interaction) -> None:
        if not self.session.match.next_round():
            await interaction.response.send_message("The next round already started.", ephemeral=True)
            return
        self.session.touch()
        await interaction.response.defer()
        await self.session.update()

    async def _rematch(self, interaction: discord.Interaction) -> None:
        await self.session.bot.rematch(self.session, interaction)


class GameButton(discord.ui.Button):
    def __init__(self, view: MatchView, control: Control, locked: bool):
        super().__init__(
            label=(control.label or ("•" if not control.emoji else None)),
            emoji=(control.emoji or None),
            style=STYLES.get(control.style, discord.ButtonStyle.secondary),
            row=max(0, min(4, control.row)),
            disabled=locked or control.disabled,
            custom_id=f"ttb:{control.id}",
        )
        self.parent_view = view
        self.action = control.id

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.parent_view.handle(interaction, self.action)


class GameSelect(discord.ui.Select):
    def __init__(self, view: MatchView, spec: Select, locked: bool):
        options = [
            discord.SelectOption(label=o.label[:100], value=o.id[:100], emoji=(o.emoji or None), description=(o.description or None))
            for o in spec.options[:25]
        ]
        super().__init__(
            placeholder=spec.placeholder[:150] or "Choose…",
            options=options,
            row=max(0, min(4, spec.row)),
            disabled=locked or spec.disabled or not options,
            custom_id=f"ttb:sel:{spec.placeholder[:40]}",
        )
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.parent_view.handle(interaction, self.values[0])


class ModalButton(discord.ui.Button):
    def __init__(self, view: MatchView, spec, locked: bool):
        super().__init__(
            label=(spec.button_label or "Type")[:80],
            emoji=(spec.button_emoji or None),
            style=STYLES.get(spec.style, discord.ButtonStyle.primary),
            row=max(0, min(4, spec.row)),
            disabled=locked or spec.disabled,
            custom_id=f"ttb:modal:{spec.id}",
        )
        self.parent_view = view
        self.spec = spec

    async def callback(self, interaction: discord.Interaction) -> None:
        match: Match = self.parent_view.session.match
        player = match.player_by_id(interaction.user.id)
        if player is None or player.index not in match.acting():
            await self.parent_view.handle(interaction, "spectator-check")
            return
        await interaction.response.send_modal(TextModal(self.parent_view, self.spec))


class TextModal(discord.ui.Modal):
    def __init__(self, view: MatchView, spec):
        super().__init__(title=spec.title[:45] or "Your answer")
        self.parent_view = view
        self.spec = spec
        self.field = discord.ui.TextInput(
            label=spec.label[:45] or "Answer",
            placeholder=(spec.placeholder or "")[:100],
            default=(spec.value or "")[:100],
            max_length=max(1, min(100, spec.max_length)),
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.parent_view.handle(interaction, f"{self.spec.id}{self.field.value}")
