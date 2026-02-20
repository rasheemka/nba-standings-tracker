#!/usr/bin/env python3
"""
Update NBA data locally and save to cache file for deployment.
Uses ESPN API exclusively — no stats.nba.com dependency.
"""

import json
import os
from datetime import datetime
from nba_tracker import (
    fetch_team_stats,
    calculate_friend_totals,
    calculate_friend_historical_standings,
    fetch_todays_games_espn,
    fetch_yesterdays_games_espn,
    update_historical_from_espn,
    get_remaining_head_to_head,
)

CACHE_FILE = 'nba_data_cache.json'

# Load existing cache — we'll incrementally update historical data
old_cache = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, 'r') as f:
            old_cache = json.load(f)
        print(f"📂 Loaded existing cache (last updated: {old_cache.get('last_updated', 'unknown')})")
    except Exception:
        pass

print("Fetching team stats from ESPN...")
team_stats = fetch_team_stats()

if team_stats:
    print(f"✅ Got stats for {len(team_stats)} teams")
    
    print("Calculating friend totals...")
    friend_totals = calculate_friend_totals(team_stats)
    
    # --- Historical data: incremental update from cached data ---
    print("Updating historical data incrementally from ESPN...")
    team_records = old_cache.get('team_records', {})
    dates = old_cache.get('dates', [])
    
    if team_records and dates:
        print(f"  Cached history has {len(dates)} dates through {dates[-1]}")
        team_records, dates = update_historical_from_espn(team_records, dates)
        friend_history = calculate_friend_historical_standings(team_records, dates)
    else:
        print("  ⚠️  No cached historical data — keeping old friend_history if available")
        friend_history = old_cache.get('friend_history')
    
    # --- Today's and yesterday's games from ESPN ---
    print("Fetching today's games from ESPN...")
    todays_games = fetch_todays_games_espn()
    
    print("Fetching yesterday's games from ESPN...")
    yesterdays_games = fetch_yesterdays_games_espn()
    
    cache_data = {
        'last_updated': datetime.now().isoformat(),
        'team_stats': team_stats,
        'friend_totals': friend_totals,
        'friend_history': friend_history,
        'todays_games': todays_games,
        'yesterdays_games': yesterdays_games,
        'team_records': team_records,
        'dates': dates,
    }
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"\n✅ Successfully fetched data for {len(team_stats)} teams")
    if friend_history:
        print(f"✅ Historical data: {len(dates)} dates (through {dates[-1] if dates else '?'})")
    if todays_games:
        print(f"✅ Today's games: {len(todays_games)} games")
    if yesterdays_games:
        print(f"✅ Yesterday's games: {len(yesterdays_games)} completed")
    print(f"✅ Saved to {CACHE_FILE}")
    print(f"✅ Last updated: {cache_data['last_updated']}")
    print("\nNow run:")
    print("  git add nba_data_cache.json")
    print("  git commit -m 'Update NBA data'")
    print("  git push")
else:
    print("❌ Failed to fetch team stats from ESPN")
    exit(1)
