# slippi-2-go

A Discord bot that syncs Slippi rank data to your server — giving players a nickname prefix and a colored role that reflects their current ELO tier.

## Features

| Command | Who | What it does |
|---|---|---|
| `/register <code>` | Anyone | Links your Slippi connect code, sets nickname + rank role |
| `/rank [@member]` | Anyone | Shows ELO, tier, W/L for yourself or another member |
| `/update` | Anyone | Manually refreshes your own rank right now |
| `/leaderboard` | Anyone | Top 10 players in the server by ELO |
| `/unregister` | Anyone | Removes your link, nickname prefix, and rank role |
| `/setup` | Admin | Creates rank roles and runs the first sync |
| `/forceupdate` | Admin | Forces an immediate rank sync for all members |

Ranks auto-refresh on a configurable interval (default 45 min) — polite to Slippi's unofficial API.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — see comments inside for each variable
```

### 3. Create the Discord application

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. **New Application** → give it a name
3. **Bot** tab → **Add Bot** → copy the token into `DISCORD_TOKEN` in `.env`
4. Under **Privileged Gateway Intents**, enable **Server Members Intent**
5. **OAuth2 → URL Generator** → scopes: `bot`, `applications.commands` → permissions below → copy the link and invite the bot to your server

**Required bot permissions:**
- Manage Roles
- Manage Nicknames
- Send Messages
- Embed Links
- Use Application Commands

> The bot's role must be **above** all rank roles in Server Settings → Roles, or it won't be able to assign them.

### 4. Get your Guild (Server) ID

Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode), then right-click your server icon → **Copy Server ID**. Paste it into `GUILD_ID` in `.env`.

### 5. Run the bot

```bash
python -m bot.main
```

On first run, an admin should type `/setup` in any channel. This creates the rank roles (Bronze, Silver, Gold, Platinum, Diamond, Master, Grandmaster) and runs the initial sync.

## Project Layout

```
slippi-2-go/
├── bot/
│   ├── main.py           # Entry point, scheduler
│   ├── slippi.py         # Slippi GraphQL client + ELO → tier mapping
│   ├── database.py       # SQLite via aiosqlite
│   ├── rank_sync.py      # Background sync logic, nickname/role updates
│   └── cogs/
│       ├── registration.py   # /register, /unregister
│       ├── rank.py           # /rank, /update, /leaderboard
│       └── admin.py          # /setup, /forceupdate
├── .env.example
├── requirements.txt
├── TESTING.md            # Step-by-step test guide
└── README.md
```

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | — | **Required.** Bot token from Discord Developer Portal |
| `GUILD_ID` | — | Your server's ID. Enables instant slash command sync during dev. Leave blank for global sync (takes ~1 hr). |
| `DB_PATH` | `slippi_bot.db` | Path to the SQLite database file |
| `SYNC_INTERVAL_MINUTES` | `45` | How often the background job refreshes all registered players |

## Hosting

For a persistent bot (always-on), deploy to:

- **Railway** — `railway up`, free tier works for small servers
- **Fly.io** — `fly launch`, generous free tier
- **Any VPS** — run with `nohup python -m bot.main &` or a systemd service

## Notes

- Slippi's GraphQL endpoint is **unofficial and undocumented**. If it goes down, the bot falls back gracefully (keeps last known rank data, logs warnings). Watch the console for `Could not fetch Slippi data` messages.
- Discord does not allow bots to modify the **server owner's** nickname.
- Nicknames are capped at 32 characters — long display names will be truncated.
- On seasonal rank resets, players with no ranked data will be marked "Unranked" until they complete placement matches.
