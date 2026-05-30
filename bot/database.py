"""SQLite persistence layer via aiosqlite."""

from __future__ import annotations

import aiosqlite


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id                TEXT PRIMARY KEY,
                welcome_channel_id      TEXT,
                leaderboard_channel_id  TEXT
            )
        """)
        for col in ("welcome_channel_id", "leaderboard_channel_id"):
            try:
                await db.execute(f"ALTER TABLE guild_config ADD COLUMN {col} TEXT")
                await db.commit()
            except Exception:
                pass
                guild_id           TEXT PRIMARY KEY,
                welcome_channel_id TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                discord_id   TEXT PRIMARY KEY,
                connect_code TEXT NOT NULL,
                display_name TEXT,
                elo          REAL,
                tier         TEXT,
                sub_tier     TEXT,
                wins         INTEGER DEFAULT 0,
                losses       INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)
        # Add sub_tier column to existing databases that predate this field
        try:
            await db.execute("ALTER TABLE registrations ADD COLUMN sub_tier TEXT")
            await db.commit()
        except Exception:
            pass
        await db.commit()


async def register_player(
    db_path: str,
    discord_id: str,
    connect_code: str,
    display_name: str,
    elo: float | None,
    tier: str,
    sub_tier: str,
    wins: int,
    losses: int,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT INTO registrations
                (discord_id, connect_code, display_name, elo, tier, sub_tier, wins, losses, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(discord_id) DO UPDATE SET
                connect_code = excluded.connect_code,
                display_name = excluded.display_name,
                elo          = excluded.elo,
                tier         = excluded.tier,
                sub_tier     = excluded.sub_tier,
                wins         = excluded.wins,
                losses       = excluded.losses,
                last_updated = excluded.last_updated
        """, (discord_id, connect_code, display_name, elo, tier, sub_tier, wins, losses))
        await db.commit()


async def get_player_by_code(db_path: str, connect_code: str) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM registrations WHERE connect_code = ?", (connect_code,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def unregister_player(db_path: str, discord_id: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "DELETE FROM registrations WHERE discord_id = ?", (discord_id,)
        )
        await db.commit()
        return cur.rowcount > 0


async def get_player(db_path: str, discord_id: str) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM registrations WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_players(db_path: str) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM registrations ORDER BY elo DESC NULLS LAST") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_player_stats(
    db_path: str,
    discord_id: str,
    display_name: str,
    elo: float | None,
    tier: str,
    sub_tier: str,
    wins: int,
    losses: int,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            UPDATE registrations
            SET display_name = ?, elo = ?, tier = ?, sub_tier = ?, wins = ?, losses = ?, last_updated = datetime('now')
            WHERE discord_id = ?
        """, (display_name, elo, tier, sub_tier, wins, losses, discord_id))
        await db.commit()


async def get_welcome_channel(db_path: str, guild_id: str) -> str | None:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT welcome_channel_id FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_welcome_channel(db_path: str, guild_id: str, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT INTO guild_config (guild_id, welcome_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET welcome_channel_id = excluded.welcome_channel_id
        """, (guild_id, channel_id))
        await db.commit()


async def get_leaderboard_channel(db_path: str, guild_id: str) -> str | None:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT leaderboard_channel_id FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_leaderboard_channel(db_path: str, guild_id: str, channel_id: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT INTO guild_config (guild_id, leaderboard_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET leaderboard_channel_id = excluded.leaderboard_channel_id
        """, (guild_id, channel_id))
        await db.commit()
