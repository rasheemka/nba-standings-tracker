#!/usr/bin/env python3
"""
Update NBA data locally and save to cache file for deployment
Run this script locally before deploying to refresh the data
"""

import json
from datetime import datetime
from nba_tracker import fetch_team_stats, calculate_friend_totals

print("Fetching NBA data from your local machine...")
team_stats = fetch_team_stats()

if team_stats:
    friend_totals = calculate_friend_totals(team_stats)
    
    cache_data = {
        'last_updated': datetime.now().isoformat(),
        'team_stats': team_stats,
        'friend_totals': friend_totals
    }
    
    with open('nba_data_cache.json', 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"✅ Successfully fetched data for {len(team_stats)} teams")
    print(f"✅ Saved to nba_data_cache.json")
    print(f"✅ Last updated: {cache_data['last_updated']}")
    print("\nNow run:")
    print("  git add nba_data_cache.json")
    print("  git commit -m 'Update NBA data'")
    print("  git push")
else:
    print("❌ Failed to fetch NBA data")
    exit(1)
