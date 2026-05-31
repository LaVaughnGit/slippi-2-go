"""Slash commands: /rank, /update, /leaderboard."""

from __future__ import annotations

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from .. import database as db
from .. import slippi
from ..rank_sync import _apply_rank


def _pos_indicator(prev: Optional[int], curr: int) -> str:
    if prev is None:
        return ""
    delta = prev - curr  # positive = moved up (lower position number = better)
    if delta > 0:
        return f" 🌲+{delta}"
    if delta < 0:
        return f" 🔻{delta}"
    return ""


def _rank_embed(
    player: dict,
    member: Optional[discord.Member] = None,
    server_rank: Optional[int] = None,
    server_total: Optional[int] = None,
) -> discord.Embed:
    elo_str = f"{player['elo']:.2f}" if player.get("elo") is not None else "Unranked"
    total = (player.get("wins") or 0) + (player.get("losses") or 0)
    winrate = f"{player['wins'] / total * 100:.1f}%" if total > 0 else "N/A"

    embed = discord.Embed(
        title=f"{player.get('tier_emoji', '')} {player['display_name']}",
        color=discord.Color(slippi.TIER_COLORS.get(player.get("tier", ""), 0x7289DA)),
    )
    embed.add_field(name="Connect Code", value=player.get("connect_code", "—"), inline=True)
    rank_display = player.get("sub_tier") or player.get("tier", "—")
    embed.add_field(name="Rank", value=f"{player.get('tier_emoji','')} {rank_display}", inline=True)
    embed.add_field(name="ELO", value=elo_str, inline=True)
    embed.add_field(name="Wins", value=str(player.get("wins", 0)), inline=True)
    embed.add_field(name="Losses", value=str(player.get("losses", 0)), inline=True)
    embed.add_field(name="Win Rate", value=winrate, inline=True)
    if server_rank is not None and server_total is not None:
        embed.add_field(name="Server Placement", value=f"#{server_rank} of {server_total}", inline=True)
    if player.get("daily_global_placement"):
        embed.add_field(name="Global Rank", value=f"#{player['daily_global_placement']}", inline=True)
    if member:
        embed.set_thumbnail(url=member.display_avatar.url)
    if player.get("last_updated"):
        embed.set_footer(text=f"Last updated: {player['last_updated']} UTC")
    return embed


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot, db_path: str):
        self.bot = bot
        self.db_path = db_path

    @app_commands.command(name="rank", description="Show Slippi rank for yourself or another member.")
    @app_commands.describe(member="The server member to look up (defaults to you)")
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member] = None) -> None:
        await interaction.response.defer()
        target = member or interaction.user
        player = await db.get_player(self.db_path, str(target.id))
        if player is None:
            who = "You are" if target == interaction.user else f"{target.display_name} is"
            await interaction.followup.send(
                f"{who} not registered. Use `/register <connect_code>` to link a Slippi account."
            )
            return

        disc_member = interaction.guild.get_member(target.id) if interaction.guild else None

        server_rank = None
        server_total = None
        if interaction.guild:
            all_players = await db.get_all_players(self.db_path)
            guild_ids = {
                str(p["discord_id"])
                for p in all_players
                if interaction.guild.get_member(int(p["discord_id"]))
            }
            server_players = [p for p in all_players if str(p["discord_id"]) in guild_ids]
            server_total = len(server_players)
            for i, p in enumerate(server_players):
                if str(p["discord_id"]) == str(target.id):
                    server_rank = i + 1
                    break

        embed = _rank_embed(player, disc_member, server_rank, server_total)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="update", description="Manually refresh your Slippi rank right now.")
    async def update(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        player = await db.get_player(self.db_path, str(interaction.user.id))
        if player is None:
            await interaction.followup.send(
                "You're not registered. Use `/register <connect_code>` first.", ephemeral=True
            )
            return

        async with aiohttp.ClientSession() as session:
            data = await slippi.fetch_player(player["connect_code"], session)

        if data is None:
            await interaction.followup.send(
                "⚠️ Slippi API is unreachable right now. Try again in a minute.", ephemeral=True
            )
            return

        await db.update_player_stats(
            self.db_path,
            str(interaction.user.id),
            data["display_name"],
            data["elo"],
            data["tier"],
            data["sub_tier"],
            data["wins"],
            data["losses"],
        )

        data["connect_code"] = player["connect_code"]
        if interaction.guild:
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await _apply_rank(member, data, interaction.guild)

        data["last_updated"] = "just now"
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        embed = _rank_embed(data, member)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Top 10 players in this server by ELO.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        all_players = await db.get_all_players(self.db_path)
        if not all_players:
            await interaction.followup.send("No one is registered yet. Be the first with `/register`!")
            return

        # Filter to members actually in this guild
        guild = interaction.guild
        server_players = []
        for p in all_players:
            if guild and guild.get_member(int(p["discord_id"])):
                server_players.append(p)

        if not server_players:
            await interaction.followup.send("No registered members found in this server.")
            return

        guild_id = str(guild.id) if guild else ""
        prev_positions = await db.get_leaderboard_positions(self.db_path, guild_id)
        leaderboard_name = await db.get_leaderboard_name(self.db_path, guild_id) or "Server Leaderboard"

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        new_positions = {}
        for i, p in enumerate(server_players[:10]):
            curr_pos = i + 1
            did = p["discord_id"]
            new_positions[did] = curr_pos
            pos = medals[i] if i < 3 else f"`{i+1}.`"
            elo = f"{p['elo']:.0f}" if p.get("elo") is not None else "—"
            member = guild.get_member(int(did)) if guild else None
            name = member.display_name if member else p["display_name"]
            rank_display = p.get("sub_tier") or p.get("tier", "?")
            indicator = _pos_indicator(prev_positions.get(did), curr_pos)
            lines.append(f"{pos} **{name}** — {p.get('tier_emoji','')} {rank_display} (**{elo}** ELO){indicator}")

        await db.save_leaderboard_positions(self.db_path, guild_id, new_positions)

        embed = discord.Embed(
            title=f"🏆 {leaderboard_name}",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Rankings refresh automatically every ~20 minutes")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    db_path = bot.db_path  # type: ignore[attr-defined]
    await bot.add_cog(Rank(bot, db_path))
