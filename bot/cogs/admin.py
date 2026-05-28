"""Admin slash commands: /setup."""

import discord
from discord import app_commands
from discord.ext import commands

from ..rank_sync import setup_rank_roles, sync_all


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot, db_path: str):
        self.bot = bot
        self.db_path = db_path

    @app_commands.command(name="setup", description="[Admin] Create rank roles and run the first rank sync.")
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("This command must be run in a server.", ephemeral=True)
            return

        created = await setup_rank_roles(interaction.guild)
        msg = (
            f"✅ Created {len(created)} role(s): {', '.join(created)}"
            if created
            else "✅ All rank roles already exist."
        )

        await interaction.followup.send(
            f"{msg}\n\nRunning initial rank sync — this may take a moment...",
            ephemeral=True,
        )
        await sync_all(self.bot, self.db_path)
        await interaction.followup.send("✅ Initial sync complete!", ephemeral=True)

    @app_commands.command(name="admin-unregister", description="[Admin] Remove a member's Slippi registration.")
    @app_commands.describe(member="The member to unregister")
    @app_commands.default_permissions(administrator=True)
    async def admin_unregister(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        from .. import database as db2
        from ..rank_sync import RANK_ROLE_NAMES
        removed = await db2.unregister_player(self.db_path, str(member.id))
        if not removed:
            await interaction.followup.send(f"{member.mention} isn't registered.", ephemeral=True)
            return
        rank_roles = [r for r in member.roles if r.name in RANK_ROLE_NAMES]
        if rank_roles:
            try:
                await member.remove_roles(*rank_roles, reason="Admin unregister")
            except discord.Forbidden:
                pass
        try:
            await member.edit(nick=None)
        except discord.Forbidden:
            pass
        await interaction.followup.send(f"✅ Unregistered {member.mention} and cleared their rank.", ephemeral=True)

    @app_commands.command(name="forceupdate", description="[Admin] Force a rank sync for all registered members now.")
    @app_commands.default_permissions(administrator=True)
    async def force_update(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await sync_all(self.bot, self.db_path)
        await interaction.followup.send("✅ Rank sync complete for all registered members.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    db_path = bot.db_path  # type: ignore[attr-defined]
    await bot.add_cog(Admin(bot, db_path))
