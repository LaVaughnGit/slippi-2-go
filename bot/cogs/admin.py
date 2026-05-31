"""Admin slash commands: /setup."""

import discord
from discord import app_commands
from discord.ext import commands

from .. import database as db
from ..rank_sync import setup_rank_roles, sync_all
from ..scheduled_posts import post_leaderboard


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

    @app_commands.command(name="set-welcome-channel", description="[Admin] Set the channel where join prompts are posted.")
    @app_commands.describe(channel="The channel to post welcome messages in")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("Run this in a server.", ephemeral=True)
            return
        await db.set_welcome_channel(self.db_path, str(interaction.guild.id), str(channel.id))
        await interaction.followup.send(f"✅ Welcome messages will now be posted in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="admin-unregister", description="[Admin] Remove a member's Slippi registration.")
    @app_commands.describe(member="The member to unregister")
    @app_commands.default_permissions(administrator=True)
    async def admin_unregister(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        from ..rank_sync import RANK_ROLE_NAMES
        removed = await db.unregister_player(self.db_path, str(member.id))
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

    @app_commands.command(name="set-leaderboard-channel", description="[Admin] Set the channel for scheduled leaderboard posts.")
    @app_commands.describe(channel="The channel to post leaderboards in")
    @app_commands.default_permissions(administrator=True)
    async def set_leaderboard_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("Run this in a server.", ephemeral=True)
            return
        await db.set_leaderboard_channel(self.db_path, str(interaction.guild.id), str(channel.id))
        await interaction.followup.send(
            f"✅ Leaderboard posts will appear in {channel.mention}.\n"
            "Schedule: opening midnight PT · closing 11:59 PM PT · every 4 days starting May 31.",
            ephemeral=True,
        )

    @app_commands.command(name="rename-leaderboard", description="[Admin] Set a custom name for the leaderboard.")
    @app_commands.describe(name="The new leaderboard title (emojis allowed)")
    @app_commands.default_permissions(administrator=True)
    async def rename_leaderboard(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("Run this in a server.", ephemeral=True)
            return
        await db.set_leaderboard_name(self.db_path, str(interaction.guild.id), name)
        await interaction.followup.send(f"✅ Leaderboard name set to: **{name}**", ephemeral=True)

    @app_commands.command(name="post-leaderboard", description="[Admin] Post the leaderboard right now.")
    @app_commands.default_permissions(administrator=True)
    async def post_leaderboard_now(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await post_leaderboard(self.bot, self.db_path, "Current")
        await interaction.followup.send("✅ Leaderboard posted.", ephemeral=True)

    @app_commands.command(name="forceupdate", description="[Admin] Force a rank sync for all registered members now.")
    @app_commands.default_permissions(administrator=True)
    async def force_update(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await sync_all(self.bot, self.db_path)
        await interaction.followup.send("✅ Rank sync complete for all registered members.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    db_path = bot.db_path  # type: ignore[attr-defined]
    await bot.add_cog(Admin(bot, db_path))
