#!/usr/bin/env python3
"""
Roll the tracker over to a new season.

    python3 new_season.py 2026-27 --start 2026-10-20 --end 2027-04-11

What it does:
  1. Archives the current cache to seasons/<old-season>/data.json (skipped if
     that file already exists), recording the winner.
  2. Adds the new season to season_config.json with the previous season's team
     assignments copied in as a placeholder — record the draft with draft.py,
     which overwrites them.
  3. Resets nba_data_cache.json to an empty shell for the new season.

Then commit season_config.json, seasons/, and nba_data_cache.json.
"""

import argparse
import json
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'season_config.json')
CACHE_FILE = os.path.join(BASE_DIR, 'nba_data_cache.json')
SEASONS_DIR = os.path.join(BASE_DIR, 'seasons')


def archive_current(config, old_id):
    old = config['seasons'][old_id]
    dest = os.path.join(SEASONS_DIR, old_id, 'data.json')
    if os.path.exists(dest):
        print(f"• {old_id} already archived at {os.path.relpath(dest, BASE_DIR)}")
        return
    if not os.path.exists(CACHE_FILE):
        print(f"• No cache to archive for {old_id}")
        return

    with open(CACHE_FILE) as f:
        cache = json.load(f)
    totals = {k: v for k, v in cache.get('friend_totals', {}).items() if k != 'Undrafted'}
    winner, winner_record = '', ''
    if totals:
        winner, ws = max(totals.items(), key=lambda kv: kv[1]['win_pct'])
        winner_record = f"{ws['total_wins']}-{ws['total_losses']}"

    archive = {
        'season': old_id,
        'season_display': old.get('display_name', old_id),
        'start_date': old['start_date'],
        'end_date': old['end_date'],
        'status': 'completed',
        'team_assignments': old['team_assignments'],
        'draft': old.get('draft'),
        'win_totals': old.get('win_totals'),
        'winner': winner,
        'winner_record': winner_record,
        **{k: cache.get(k) for k in ('team_stats', 'friend_totals', 'friend_history',
                                     'team_records', 'dates', 'full_season_schedule')},
    }
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w') as f:
        json.dump(archive, f, indent=2)
    print(f"✅ Archived {old_id} → {os.path.relpath(dest, BASE_DIR)} (winner: {winner} {winner_record})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('season_id', help='e.g. 2026-27')
    p.add_argument('--start', required=True, help='first regular-season game, YYYY-MM-DD')
    p.add_argument('--end', required=True, help='last regular-season game, YYYY-MM-DD')
    args = p.parse_args()

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    old_id = config['current_season']
    if args.season_id == old_id:
        sys.exit(f"{args.season_id} is already the current season.")
    if args.season_id in config['seasons']:
        sys.exit(f"{args.season_id} already exists in season_config.json.")

    archive_current(config, old_id)
    config['seasons'][old_id]['status'] = 'completed'

    # ESPN's season id is the calendar year the season ends in.
    espn_year = int(args.end[:4])
    config['seasons'][args.season_id] = {
        'display_name': args.season_id,
        'start_date': args.start,
        'end_date': args.end,
        'espn_season_year': espn_year,
        'status': 'active',
        'data_file': f'seasons/{args.season_id}/data.json',
        'team_assignments': config['seasons'][old_id]['team_assignments'],
    }
    config['current_season'] = args.season_id
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ season_config.json: current season is now {args.season_id}")

    if os.path.exists(CACHE_FILE):
        shutil.copy(CACHE_FILE, CACHE_FILE + '.bak')
    with open(CACHE_FILE, 'w') as f:
        json.dump({'season': args.season_id, 'last_updated': None, 'team_stats': {},
                   'friend_totals': {}, 'friend_history': None, 'todays_games': [],
                   'yesterdays_games': [], 'team_records': {}, 'dates': [],
                   'full_season_schedule': None}, f, indent=2)
    print(f"✅ Reset nba_data_cache.json (backup at nba_data_cache.json.bak)")
    print(f"\n➡️  Record the draft with draft.py, and add this season's win_totals "
          f"to season_config.json for the Research and Draft pages.")


if __name__ == '__main__':
    main()
