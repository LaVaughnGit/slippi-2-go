# Testing the Slippi Rank Bot

This guide walks you through verifying every feature on a real Discord server.

## Prerequisites

- Python 3.11+ installed
- A Discord account with a test server where **you are the owner** (so you can manage roles and give the bot admin)
- A real Slippi connect code to test with (yours, or borrow a known-active one)

---

## Step 1 — Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in the env file
cp .env.example .env
```

Open `.env` and set:
- `DISCORD_TOKEN` — from the Discord Developer Portal (see README)
- `GUILD_ID` — your test server's ID
- Leave `DB_PATH` and `SYNC_INTERVAL_MINUTES` at their defaults for now

---

## Step 2 — Bot Permissions & Role Hierarchy

1. Invite the bot to your test server using the OAuth2 URL from the Developer Portal (scopes: `bot` + `applications.commands`, permissions: Manage Roles, Manage Nicknames, Send Messages, Embed Links, Use Application Commands).
2. Go to **Server Settings → Roles**.
3. Drag the bot's role to the **top** of the list (above everyone else). This is required for it to assign roles and edit nicknames.

---

## Step 3 — Start the Bot

```bash
python -m bot.main
```

You should see log output like:
```
[INFO] Loaded cog: bot.cogs.registration
[INFO] Loaded cog: bot.cogs.rank
[INFO] Loaded cog: bot.cogs.admin
[INFO] Slash commands synced to guild <your_id>
[INFO] Rank sync scheduler started — interval: 45 minutes
[INFO] Logged in as YourBotName#1234
```

If slash commands don't appear immediately, wait 5–10 seconds and reload Discord.

---

## Step 4 — First-Time Setup

In any channel in your test server, type:
```
/setup
```

**Expected:** The bot replies (ephemeral) that it created the rank roles (Bronze, Silver, Gold, Platinum, Diamond, Master, Grandmaster) and ran the initial sync. Check **Server Settings → Roles** — you should see seven new colored roles.

---

## Step 5 — Register a Player

```
/register ABC#123
```
(Use a real connect code — made-up ones will fail the Slippi lookup.)

**Expected:**
- Ephemeral embed showing the player's display name, ELO, tier, and W/L
- Your server nickname changes to something like `[💎 ABC#123] YourName`
- A rank role (e.g. "Diamond") is added to your profile

**Edge case — bad connect code:**
```
/register FAKE#999
```
**Expected:** Error message saying the code wasn't found. No nickname or role change.

---

## Step 6 — View Rank

```
/rank
```
**Expected:** Public embed with your ELO, tier, wins, losses, win rate, and last-updated timestamp.

```
/rank @AnotherMember
```
**Expected:** Same embed but for that member (if they're registered). Error message if they're not.

---

## Step 7 — Manual Update

```
/update
```
**Expected:** Ephemeral embed with freshly fetched stats. Nickname and role update if rank changed.

To verify it's actually fetching live: note your current W/L, play a couple of ranked games on Slippi, then run `/update` again — the numbers should change.

---

## Step 8 — Leaderboard

Register a second account (or ask a friend) to get more than one entry, then:
```
/leaderboard
```
**Expected:** Embed listing up to 10 registered members in the server, sorted by ELO descending, with medal emojis for the top 3.

---

## Step 9 — Unregister

```
/unregister
```
**Expected:**
- Ephemeral confirmation message
- Rank role removed from your profile
- Nickname reset to your actual username

---

## Step 10 — Admin Force Sync

```
/forceupdate
```
(Must be run by a server administrator.)

**Expected:** Bot syncs all registered members immediately and replies with a confirmation. Check the console — you should see log lines for each player synced with a 1.5-second delay between them.

---

## Step 11 — Background Sync (optional smoke test)

To verify the scheduler works without waiting 45 minutes, temporarily lower `SYNC_INTERVAL_MINUTES=1` in `.env`, restart the bot, and watch the console. You should see sync log output every ~60 seconds. Set it back to `45` when done.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Slash commands not appearing | Guild ID missing or wrong | Check `GUILD_ID` in `.env`; guild-scoped commands appear instantly, global take ~1 hr |
| "Missing Permissions" error on nickname | Bot role is below the target member's highest role | Move the bot's role to the top in Server Settings → Roles |
| Slippi data returns `None` | API is temporarily down or connect code format wrong | Ensure code is `ABC#123` format (letter-hash-numbers); check console logs |
| `DISCORD_TOKEN` error on startup | Token not set or invalid | Re-copy token from Discord Developer Portal → Bot tab |
| Roles not created by `/setup` | Bot lacks Manage Roles permission | Re-invite with the correct OAuth2 permissions |

---

## What to Verify Before Considering It "Done"

- [ ] `/setup` creates all 7 rank roles with correct colors
- [ ] `/register` with a valid code sets nickname and role
- [ ] `/register` with an invalid code shows a clear error
- [ ] `/rank` shows correct embed data
- [ ] `/rank @member` works for registered members, errors for unregistered
- [ ] `/update` fetches fresh data and updates nickname/role
- [ ] `/leaderboard` sorts correctly with multiple registered users
- [ ] `/unregister` cleans up nickname and role
- [ ] `/forceupdate` runs a full sync (check console logs)
- [ ] Background scheduler fires on the configured interval (console logs)
- [ ] Bot gracefully handles Slippi API being slow or unreachable (logs a warning, doesn't crash)
