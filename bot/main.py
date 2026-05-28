"""Entry point — loads cogs, initialises DB, starts the background sync scheduler."""

from __future__ import annotations

import asyncio
import logging
import os

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from dotenv import load_dotenv

from . import database as db
from .rank_sync import sync_all

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

COGS = [
    "bot.cogs.registration",
    "bot.cogs.rank",
    "bot.cogs.admin",
]


class SlippiBot(commands.Bot):
    def __init__(self, db_path: str, guild_id: int | None):
        intents = discord.Intents.default()
        intents.members = True  # needed to edit nicknames and roles
        super().__init__(command_prefix="!", intents=intents)
        self.db_path = db_path
        self.guild_id = guild_id
        self.scheduler = AsyncIOScheduler()

    async def setup_hook(self) -> None:
        await db.init_db(self.db_path)

        for cog in COGS:
            await self.load_extension(cog)
            log.info("Loaded cog: %s", cog)

        # Sync slash commands — guild-scoped for instant availability during dev,
        # swap to global (remove guild=...) for production.
        if self.guild_id:
            guild_obj = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            log.info("Slash commands synced to guild %d", self.guild_id)
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally (may take up to 1 hour to propagate)")

        # Background rank refresh
        interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "45"))
        self.scheduler.add_job(
            sync_all,
            "interval",
            minutes=interval,
            args=[self, self.db_path],
            id="rank_sync",
        )
        self.scheduler.start()
        log.info("Rank sync scheduler started — interval: %d minutes", interval)

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)  # type: ignore[union-attr]

    async def close(self) -> None:
        self.scheduler.shutdown(wait=False)
        await super().close()


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")

    raw_guild = os.getenv("GUILD_ID", "").strip()
    guild_id = int(raw_guild) if raw_guild else None
    db_path = os.getenv("DB_PATH", "slippi_bot.db")

    bot = SlippiBot(db_path=db_path, guild_id=guild_id)
    asyncio.run(bot.start(token))


if __name__ == "__main__":
    main()
