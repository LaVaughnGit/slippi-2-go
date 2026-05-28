"""Background rank sync — polls all registered players and updates nicknames/roles."""

import asyncio
import logging

import aiohttp
import discord

from . import database as db
from . import slippi

log = logging.getLogger(__name__)

RANK_ROLE_NAMES = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster"]


def _build_nick(tier_emoji: str, sub_tier: str, connect_code: str, display_name: str) -> str:
    """
    Format: {emoji}{roman} | {username} | {code}
    Example: 🥇II | LaVaughn | SLA#827
    Truncates username to keep the suffix visible within Discord's 32-char cap.
    """
    # Extract Roman numeral from sub_tier name (e.g. "Gold II" → "II")
    parts = sub_tier.split()
    roman = parts[-1] if len(parts) > 1 and parts[-1] in ("I", "II", "III") else ""
    suffix = f" | {display_name} | {connect_code}"
    prefix = f"{tier_emoji}{roman}"
    total = len(prefix) + len(suffix)
    if total > 32:
        trim = 32 - len(prefix) - len(f" | ... | {connect_code}")
        display_name = display_name[:max(trim, 1)] + "…"
        suffix = f" | {display_name} | {connect_code}"
    return (prefix + suffix)[:32]


async def _apply_rank(member: discord.Member, player_data: dict, guild: discord.Guild) -> None:
    """Update a single member's nickname and rank role."""
    tier = player_data["tier"]
    sub_tier = player_data.get("sub_tier", tier)
    emoji = player_data["tier_emoji"]
    code = player_data.get("connect_code", "")

    # Nickname
    base_name = member.global_name or member.name
    new_nick = _build_nick(emoji, sub_tier, code, base_name)
    log.info("Nick update for %s: '%s' → '%s'", member, member.nick, new_nick)
    try:
        if member.nick != new_nick:
            await member.edit(nick=new_nick)
            log.info("Nick updated successfully for %s", member)
        else:
            log.info("Nick unchanged for %s", member)
    except discord.Forbidden:
        log.warning("Missing permission to change nickname for %s (bot role may be too low)", member)
    except Exception as e:
        log.error("Failed to change nickname for %s: %s", member, e)

    # Roles — remove old rank roles, add the current one
    rank_roles = {r.name: r for r in guild.roles if r.name in RANK_ROLE_NAMES}
    if not rank_roles:
        log.warning("No rank roles found in guild '%s' — run /setup first", guild.name)
        return

    roles_to_remove = [r for r in member.roles if r.name in RANK_ROLE_NAMES and r.name != tier]
    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove, reason="Rank sync")
        except discord.Forbidden:
            log.warning("Missing permission to remove roles from %s", member)

    if tier in rank_roles and rank_roles[tier] not in member.roles:
        try:
            await member.add_roles(rank_roles[tier], reason="Rank sync")
        except discord.Forbidden:
            log.warning("Missing permission to add role to %s", member)


async def sync_all(bot: discord.Client, db_path: str) -> None:
    """Fetch fresh data for every registered player and apply Discord changes."""
    players = await db.get_all_players(db_path)
    if not players:
        return

    async with aiohttp.ClientSession() as session:
        for player in players:
            guild = bot.get_guild(int(player.get("guild_id", 0) or 0))
            # We look across all guilds the bot is in
            for g in bot.guilds:
                member = g.get_member(int(player["discord_id"]))
                if member is None:
                    continue

                data = await slippi.fetch_player(player["connect_code"], session)
                if data is None:
                    log.warning("Could not fetch Slippi data for %s", player["connect_code"])
                    continue

                data["connect_code"] = player["connect_code"]
                await db.update_player_stats(
                    db_path,
                    player["discord_id"],
                    data["display_name"],
                    data["elo"],
                    data["tier"],
                    data["sub_tier"],
                    data["wins"],
                    data["losses"],
                )
                await _apply_rank(member, data, g)

                # Small delay to avoid hammering the API
                await asyncio.sleep(1.5)

    log.info("Rank sync complete for %d players", len(players))


async def setup_rank_roles(guild: discord.Guild) -> list[str]:
    """
    Ensure all rank roles exist in the guild with appropriate colors.
    Returns a list of roles that were created.
    """
    from . import slippi as sl

    existing = {r.name for r in guild.roles}
    created = []
    for tier_name, color_int in sl.TIER_COLORS.items():
        if tier_name not in existing:
            await guild.create_role(
                name=tier_name,
                color=discord.Color(color_int),
                reason="Slippi rank bot setup",
            )
            created.append(tier_name)
    return created
