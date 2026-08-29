#!/usr/bin/env python3
"""
Refresh nba_data_cache.json from ESPN for the current season.

Run by the GitHub Actions workflow twice daily; safe to run by hand any time.
"""

import json
import os
import sys
from datetime import datetime

from nba_tracker import (
    CURRENT_SEASON_ID,
    SEASON_END,
    SEASON_START,
    calculate_friend_historical_standings,
    calculate_friend_totals,
    fetch_team_stats,
    fetch_todays_games_espn,
    fetch_yesterdays_games_espn,
    load_season_schedule,
    update_historical_from_espn,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, 'nba_data_cache.json')


def main() -> int:
    today = datetime.now().strftime('%Y-%m-%d')
    if today < SEASON_START:
        print(f"Season {CURRENT_SEASON_ID} starts {SEASON_START}; nothing to update yet.")
        return 0
    if today > SEASON_END and (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(SEASON_END, '%Y-%m-%d')).days > 2:
        print(f"Season {CURRENT_SEASON_ID} ended {SEASON_END}; nothing to update. Run new_season.py when ready.")
        return 0

    old = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            old = json.load(f)
    if old.get('season') not in (None, CURRENT_SEASON_ID):
        print(f"Cache is for season {old.get('season')} but config says {CURRENT_SEASON_ID}. "
              f"Run new_season.py first.")
        return 1

    team_stats = fetch_team_stats()
    if not team_stats:
        print("❌ Failed to fetch team stats from ESPN")
        return 1

    schedule = load_season_schedule(old.get('full_season_schedule'))
    friend_totals = calculate_friend_totals(team_stats)

    print("Updating game-by-game history...")
    team_records, dates = update_historical_from_espn(old.get('team_records'), old.get('dates'))
    friend_history = calculate_friend_historical_standings(team_records, dates)

    cache = {
        'season': CURRENT_SEASON_ID,
        'last_updated': datetime.now().isoformat(timespec='seconds'),
        'team_stats': team_stats,
        'friend_totals': friend_totals,
        'friend_history': friend_history,
        'todays_games': fetch_todays_games_espn() if today <= SEASON_END else [],
        'yesterdays_games': fetch_yesterdays_games_espn(),
        'team_records': team_records,
        'dates': dates,
        'full_season_schedule': schedule,
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    print(f"✅ {len(team_stats)} teams, {len(dates)} history dates"
          f"{f' (through {dates[-1]})' if dates else ''}, "
          f"{len(schedule or [])} scheduled games → {os.path.basename(CACHE_FILE)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
