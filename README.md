# slippi-2-go

A Discord bot that syncs Slippi rank data to your server — giving players a nickname prefix and a colored role that reflects their current ELO tier. Includes a live leaderboard with placement change tracking, welcome messages, and admin tools.

## Features

### Player Commands

| Command | What it does |
|---|---|
| `/register <code>` | Links your Slippi connect code, sets nickname + rank role |
| `/rank [@member]` | Shows ELO, tier, W/L, and server placement for yourself or another member |
| `/update` | Manually refreshes your own rank right now |
| `/leaderboard` | Top 10 players in the server by ELO with placement change indicators |
| `/unregister` | Removes your link, nickname prefix, and rank role |

### Admin Commands

| Command | What it does |
|---|---|
| `/setup` | Creates rank roles and runs the first sync |
| `/forceupdate` | Forces an immediate rank sync for all members |
| `/admin-unregister @member` | Removes a member's registration and clears their rank |
| `/admin-set-code @member <code>` | Sets or changes a member's Slippi connect code |
| `/set-welcome-channel #channel` | Sets the channel where join prompts are posted |
| `/set-leaderboard-channel #channel` | Sets the channel for scheduled leaderboard posts |
| `/rename-leaderboard <name>` | Sets a custom name for the leaderboard (emojis allowed) |
| `/post-leaderboard` | Posts the leaderboard immediately |

### Automatic Features

- **Nickname formatting** — `🥇II | LaVaughn | SLA#827` updated on every sync
- **Rank roles** — Bronze through Grandmaster, colored and auto-assigned
- **Background sync** — refreshes all registered players every 20 minutes
- **Scheduled leaderboard posts** — opening (midnight PT) and closing (11:59 PM PT) every 4 days starting May 31, 2026
- **Welcome messages** — DM + server channel prompt when a new member joins
- **Placement change indicators** — 🌲+2 / 🔻-1 on leaderboard showing position shifts since last post

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
- Read Message History
- Use Application Commands

> The bot's role must be **above** all rank roles in Server Settings → Roles, or it won't be able to assign them.

### 4. Get your Guild (Server) ID

Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode), then right-click your server icon → **Copy Server ID**. Paste it into `GUILD_ID` in `.env`.

Leave `GUILD_ID` blank to sync commands globally (public bot mode — takes up to 1 hour to propagate).

### 5. Run the bot

```bash
python -m bot.main
```

On first run, an admin should type `/setup` in any channel. This creates the rank roles (Bronze, Silver, Gold, Platinum, Diamond, Master, Grandmaster) and runs the initial sync.

## Project Layout

```
slippi-2-go/
├── bot/
│   ├── main.py               # Entry point, scheduler
│   ├── slippi.py             # Slippi GraphQL client + ELO → tier mapping
│   ├── database.py           # SQLite via aiosqlite
│   ├── rank_sync.py          # Background sync logic, nickname/role updates
│   ├── scheduled_posts.py    # Scheduled leaderboard posting
│   └── cogs/
│       ├── registration.py   # /register, /unregister, on_member_join
│       ├── rank.py           # /rank, /update, /leaderboard
│       └── admin.py          # All admin commands
├── Procfile                  # Railway deployment
├── .env.example
├── requirements.txt
└── README.md
```

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | — | **Required.** Bot token from Discord Developer Portal |
| `GUILD_ID` | — | Your server's ID for instant slash command sync. Leave blank for global sync. |
| `DB_PATH` | `slippi_bot.db` | Path to the SQLite database file |
| `SYNC_INTERVAL_MINUTES` | `20` | How often the background job refreshes all registered players |

## Deploying to Railway

1. Push the repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. In the **Variables** tab, add `DISCORD_TOKEN`, `SYNC_INTERVAL_MINUTES`, and `DB_PATH`
4. Leave `GUILD_ID` blank for a public bot, or set it to your server ID for a single-server bot
5. Railway deploys automatically on every push

> **Note:** SQLite is file-based. The database resets on each redeploy. For persistent data across deploys, use a Railway Volume (Hobby plan required) mounted at `/data` and set `DB_PATH=/data/slippi_bot.db`.

## Notes

- Slippi's GraphQL endpoint is **unofficial and undocumented**. If it goes down, the bot falls back gracefully (keeps last known rank data, logs warnings).
- Discord does not allow bots to modify the **server owner's** nickname.
- Nicknames are capped at 32 characters — long display names will be truncated.
- Connect codes are unique per Discord user — duplicate registrations are blocked. Admins can resolve disputes with `/admin-unregister` or `/admin-set-code`.
- On seasonal rank resets, players with no ranked data will be marked "Unranked" until they complete placement matches.
