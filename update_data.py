#!/usr/bin/env python3
"""
Update NBA data locally and save to cache file for deployment
Run this script locally before deploying to refresh the data
"""

import json
from datetime import datetime
from nba_tracker import fetch_team_stats, calculate_friend_totals, fetch_historical_standings, calculate_friend_historical_standings

print("Fetching NBA data from your local machine...")
team_stats = fetch_team_stats()

if team_stats:
    print("Calculating friend totals...")
    friend_totals = calculate_friend_totals(team_stats)
    
    print("Fetching historical game data for horse-race graph...")
    team_records, dates = fetch_historical_standings()
    friend_history = calculate_friend_historical_standings(team_records, dates) if team_records else None
    
    cache_data = {
        'last_updated': datetime.now().isoformat(),
        'team_stats': team_stats,
        'friend_totals': friend_totals,
        'friend_history': friend_history
    }
    
    with open('nba_data_cache.json', 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"✅ Successfully fetched data for {len(team_stats)} teams")
    if friend_history:
        print(f"✅ Historical data included for horse-race graph")
    print(f"✅ Saved to nba_data_cache.json")
    print(f"✅ Last updated: {cache_data['last_updated']}")
    print("\nNow run:")
    print("  git add nba_data_cache.json")
    print("  git commit -m 'Update NBA data'")
    print("  git push")
else:
    print("❌ Failed to fetch NBA data")
    exit(1)
