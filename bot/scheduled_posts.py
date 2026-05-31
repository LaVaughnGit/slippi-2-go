"""Scheduled leaderboard posts."""

from __future__ import annotations

import logging
from typing import Optional

import discord

from . import database as db


def _pos_indicator(prev: Optional[int], curr: int) -> str:
    if prev is None:
        return ""
    delta = prev - curr
    if delta > 0:
        return f" 🌲+{delta}"
    if delta < 0:
        return f" 🔻{delta}"
    return ""


log = logging.getLogger(__name__)


async def post_leaderboard(bot: discord.Client, db_path: str, label: str) -> None:
    """Build and post the leaderboard embed to every guild's configured channel."""
    all_players = await db.get_all_players(db_path)

    for guild in bot.guilds:
        channel_id = await db.get_leaderboard_channel(db_path, str(guild.id))
        channel = (
            guild.get_channel(int(channel_id))
            if channel_id
            else guild.system_channel
        )
        if not channel:
            continue

        server_players = [
            p for p in all_players if guild.get_member(int(p["discord_id"]))
        ]
        if not server_players:
            continue

        guild_id = str(guild.id)
        prev_positions = await db.get_leaderboard_positions(db_path, guild_id)
        leaderboard_name = await db.get_leaderboard_name(db_path, guild_id) or "Server Leaderboard"

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        new_positions = {}
        for i, p in enumerate(server_players[:10]):
            curr_pos = i + 1
            did = p["discord_id"]
            new_positions[did] = curr_pos
            pos = medals[i] if i < 3 else f"`{i+1}.`"
            elo = f"{p['elo']:.0f}" if p.get("elo") is not None else "—"
            member = guild.get_member(int(did))
            name = member.display_name if member else p["display_name"]
            rank_display = p.get("sub_tier") or p.get("tier", "?")
            indicator = _pos_indicator(prev_positions.get(did), curr_pos)
            lines.append(
                f"{pos} **{name}** — {p.get('tier_emoji','')} {rank_display} (**{elo}** ELO){indicator}"
            )

        await db.save_leaderboard_positions(db_path, guild_id, new_positions)

        embed = discord.Embed(
            title=f"🏆 {label} — {leaderboard_name}",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Next update in 4 days • /rank to check your stats")

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            log.warning("Missing permission to post leaderboard in %s / %s", guild.name, channel)
