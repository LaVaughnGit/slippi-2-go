"""Slippi GraphQL API client — unofficial endpoint, handle failures gracefully."""

from __future__ import annotations

import aiohttp

GRAPHQL_URL = "https://internal.slippi.gg"

RANKED_QUERY = """
query UserProfilePageQuery($cc: String, $uid: String) {
  getUser(connectCode: $cc, fbUid: $uid) {
    displayName
    rankedNetplayProfile {
      ratingOrdinal
      ratingUpdateCount
      wins
      losses
      dailyGlobalPlacement
      dailyRegionalPlacement
      continent
    }
  }
}
"""

# Sub-tier thresholds from slippi-launcher calculate_rank.ts
# Each entry: (min_elo, display_name, emoji, broad_tier)
RANK_TIERS = [
    (0,       "Bronze I",      "🥉", "Bronze"),
    (765.43,  "Bronze II",     "🥉", "Bronze"),
    (913.72,  "Bronze III",    "🥉", "Bronze"),
    (1054.87, "Silver I",      "🥈", "Silver"),
    (1188.88, "Silver II",     "🥈", "Silver"),
    (1315.75, "Silver III",    "🥈", "Silver"),
    (1435.48, "Gold I",        "🥇", "Gold"),
    (1548.07, "Gold II",       "🥇", "Gold"),
    (1653.52, "Gold III",      "🥇", "Gold"),
    (1751.83, "Platinum I",    "🔷", "Platinum"),
    (1843.00, "Platinum II",   "🔷", "Platinum"),
    (1927.03, "Platinum III",  "🔷", "Platinum"),
    (2003.92, "Diamond I",     "💎", "Diamond"),
    (2073.67, "Diamond II",    "💎", "Diamond"),
    (2136.28, "Diamond III",   "💎", "Diamond"),
    (2191.75, "Master I",      "👑", "Master"),
    (2275.00, "Master II",     "👑", "Master"),
    (2350.00, "Master III",    "👑", "Master"),
]

TIER_COLORS = {
    "Bronze":      0xCD7F32,
    "Silver":      0xC0C0C0,
    "Gold":        0xFFD700,
    "Platinum":    0x00BFFF,
    "Diamond":     0xB9F2FF,
    "Master":      0xFF69B4,
    "Grandmaster": 0xFFFFFF,
}


def elo_to_tier(elo: float, daily_global_placement: int | None = None, sets_played: int = 0) -> tuple[str, str, str]:
    """Return (sub_tier_name, tier_emoji, broad_tier) for a given ELO."""
    if sets_played == 0:
        return "Unranked", "❓", "Unranked"
    if daily_global_placement is not None and daily_global_placement <= 300 and elo >= 2191.75:
        return "Grandmaster", "✨", "Grandmaster"
    sub_name, emoji, broad = "Bronze I", "🥉", "Bronze"
    for threshold, name, tier_emoji, broad_tier in RANK_TIERS:
        if elo >= threshold:
            sub_name, emoji, broad = name, tier_emoji, broad_tier
    return sub_name, emoji, broad


async def fetch_player(connect_code: str, session: aiohttp.ClientSession) -> dict | None:
    """
    Query Slippi for a player's ranked profile.
    Returns a dict with keys: display_name, elo, wins, losses, tier, tier_emoji,
    daily_global_placement, daily_regional_placement.
    Returns None if the code doesn't exist or the API is unreachable.
    """
    normalized = connect_code.upper().replace("-", "#")
    try:
        async with session.post(
            GRAPHQL_URL,
            json={
                "operationName": "UserProfilePageQuery",
                "query": RANKED_QUERY,
                "variables": {"cc": normalized, "uid": normalized},
            },
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
    except Exception:
        return None

    try:
        user = data["data"]["getUser"]
        if user is None:
            return None
        profile = user["rankedNetplayProfile"]
        if profile is None:
            return {
                "display_name": user["displayName"],
                "elo": None,
                "wins": 0,
                "losses": 0,
                "tier": "Unranked",
                "tier_emoji": "❓",
                "daily_global_placement": None,
                "daily_regional_placement": None,
            }
        elo = profile["ratingOrdinal"]
        placement = profile.get("dailyGlobalPlacement")
        sets_played = profile.get("ratingUpdateCount") or 0
        sub_tier, emoji, broad_tier = elo_to_tier(elo, placement, sets_played)
        return {
            "display_name": user["displayName"],
            "elo": round(elo, 2),
            "wins": profile.get("wins", 0),
            "losses": profile.get("losses", 0),
            "tier": broad_tier,       # used for Discord role assignment
            "sub_tier": sub_tier,     # displayed in embeds (e.g. "Gold II")
            "tier_emoji": emoji,
            "daily_global_placement": placement,
            "daily_regional_placement": profile.get("dailyRegionalPlacement"),
        }
    except (KeyError, TypeError):
        return None
