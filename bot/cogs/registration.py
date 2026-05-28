"""Slash commands: /register and /unregister."""

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .. import database as db
from .. import slippi
from ..rank_sync import _apply_rank


class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot, db_path: str):
        self.bot = bot
        self.db_path = db_path

    @app_commands.command(name="register", description="Link your Slippi connect code to this server.")
    @app_commands.describe(connect_code="Your Slippi connect code (e.g. ABC#123)")
    async def register(self, interaction: discord.Interaction, connect_code: str) -> None:
        await interaction.response.defer(ephemeral=True)

        normalized = connect_code.upper().replace("-", "#")

        # Block if another Discord user already owns this code
        existing = await db.get_player_by_code(self.db_path, normalized)
        if existing and existing["discord_id"] != str(interaction.user.id):
            owner = interaction.guild.get_member(int(existing["discord_id"])) if interaction.guild else None
            owner_str = owner.mention if owner else "another member"
            await interaction.followup.send(
                f"❌ **{normalized}** is already registered to {owner_str}. "
                "If this is your code, ask a server admin to unregister it with `/admin-unregister`.",
                ephemeral=True,
            )
            return

        async with aiohttp.ClientSession() as session:
            data = await slippi.fetch_player(normalized, session)

        if data is None:
            await interaction.followup.send(
                f"❌ Couldn't find a Slippi account for **{normalized}**. "
                "Double-check your connect code and try again.",
                ephemeral=True,
            )
            return

        await db.register_player(
            self.db_path,
            str(interaction.user.id),
            normalized,
            data["display_name"],
            data["elo"],
            data["tier"],
            data["sub_tier"],
            data["wins"],
            data["losses"],
        )

        data["connect_code"] = normalized
        if interaction.guild:
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await _apply_rank(member, data, interaction.guild)

        elo_str = f"{data['elo']:.2f}" if data["elo"] is not None else "Unranked"
        embed = discord.Embed(
            title="✅ Registered!",
            description=(
                f"**Slippi name:** {data['display_name']}\n"
                f"**Connect code:** {normalized}\n"
                f"**Rank:** {data['tier_emoji']} {data['sub_tier']}\n"
                f"**ELO:** {elo_str}\n"
                f"**W/L:** {data['wins']}W / {data['losses']}L"
            ),
            color=discord.Color(slippi.TIER_COLORS.get(data["tier"], 0x7289DA)),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        embed = discord.Embed(
            title="Welcome to the server!",
            description=(
                "To get your Slippi rank displayed next to your name, "
                "head back to the server and run:\n\n"
                "```/register <your connect code>```\n"
                "For example: `/register ABC#123`\n\n"
                "Your rank, ELO, and wins/losses will be pulled automatically from Slippi "
                "and your nickname will be updated to show your current tier."
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="You can update your rank anytime with /update")
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled — nothing we can do

    @app_commands.command(name="unregister", description="Unlink your Slippi account from this server.")
    async def unregister(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        removed = await db.unregister_player(self.db_path, str(interaction.user.id))
        if not removed:
            await interaction.followup.send("You're not registered.", ephemeral=True)
            return

        # Remove rank roles
        if interaction.guild and isinstance(interaction.user, discord.Member):
            from ..rank_sync import RANK_ROLE_NAMES
            rank_roles = [r for r in interaction.user.roles if r.name in RANK_ROLE_NAMES]
            if rank_roles:
                try:
                    await interaction.user.remove_roles(*rank_roles, reason="Unregistered")
                except discord.Forbidden:
                    pass
            try:
                await interaction.user.edit(nick=None)
            except discord.Forbidden:
                pass

        await interaction.followup.send("✅ Unregistered. Your nickname and rank role have been removed.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    db_path = bot.db_path  # type: ignore[attr-defined]
    await bot.add_cog(Registration(bot, db_path))
