#!/usr/bin/env python3
"""
Render the site to static HTML in dist/.

    python3 build.py            # -> dist/
    python3 -m http.server -d dist 8000   # preview

Pages:
  /                         current season (from nba_data_cache.json)
  /seasons/                 archived seasons list
  /seasons/<id>/            one archived season
  /all-time/                cumulative records
"""

import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from nba_tracker import ALL_TEAMS, SEASON_DISPLAY, SEASON_START, TEAM_ASSIGNMENTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, 'nba_data_cache.json')
SEASONS_DIR = os.path.join(BASE_DIR, 'seasons')
DIST_DIR = os.path.join(BASE_DIR, 'dist')

env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')),
                  autoescape=select_autoescape(['html']))


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def load_season_data(season_id):
    return load_json(os.path.join(SEASONS_DIR, season_id, 'data.json'))


def get_all_seasons():
    seasons = []
    if not os.path.isdir(SEASONS_DIR):
        return seasons
    for season_dir in sorted(os.listdir(SEASONS_DIR), reverse=True):
        data = load_season_data(season_dir)
        if not data:
            continue
        seasons.append({
            'id': season_dir,
            'display_name': data.get('season_display', season_dir),
            'winner': data.get('winner', 'TBD'),
            'winner_record': data.get('winner_record', ''),
            'status': data.get('status', 'completed'),
            'start_date': data.get('start_date', ''),
            'end_date': data.get('end_date', ''),
        })
    return seasons


def rank_friends(friend_totals, exclude_undrafted=False):
    items = friend_totals.items()
    if exclude_undrafted:
        items = [(f, s) for f, s in items if f != 'Undrafted']
    return sorted(items, key=lambda x: x[1]['win_pct'], reverse=True)


def build_team_breakdown(sorted_friends, team_stats):
    breakdown = {}
    for friend, stats in sorted_friends:
        rows = []
        for team in stats['teams']:
            t = team_stats.get(team)
            if not t:
                continue
            gp = t.get('games_played', 0)
            rows.append({
                'name': team,
                'wins': t.get('wins', 0),
                'losses': t.get('losses', 0),
                'win_pct': t.get('win_pct', 0),
                'pt_diff': (t.get('total_pts_scored', 0) - t.get('total_pts_allowed', 0)) / gp if gp else 0,
            })
        rows.sort(key=lambda r: r['wins'], reverse=True)
        breakdown[friend] = rows
    return breakdown


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def write(rel_path, template, **ctx):
    """Render template to dist/<rel_path>/index.html with `root` pointing back to site root."""
    depth = len([p for p in rel_path.split('/') if p])
    ctx['root'] = '/'.join(['..'] * depth) if depth else '.'
    out_dir = os.path.join(DIST_DIR, rel_path)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'index.html'), 'w') as f:
        f.write(env.get_template(template).render(**ctx))
    print(f"  {rel_path or '/':<24} ← {template}")


def page_index():
    data = load_json(CACHE_FILE) or {}
    team_stats = data.get('team_stats') or {}
    sorted_friends = rank_friends(data.get('friend_totals') or {})
    write('', 'index.html',
          season_display=SEASON_DISPLAY,
          season_start=SEASON_START,
          sorted_friends=sorted_friends,
          team_breakdown=build_team_breakdown(sorted_friends, team_stats),
          last_updated=data.get('last_updated'),
          friend_history=data.get('friend_history'),
          todays_games=data.get('todays_games') or [],
          yesterdays_games=data.get('yesterdays_games') or [],
          sandbox_data={
              'teams': ALL_TEAMS,
              'assignments': TEAM_ASSIGNMENTS,
              'team_stats': team_stats,
              'team_records': data.get('team_records') or {},
              'dates': data.get('dates') or [],
              'schedule': data.get('full_season_schedule') or [],
          })


def page_seasons():
    seasons = get_all_seasons()
    standings = {}
    for s in seasons:
        data = load_season_data(s['id'])
        if data and data.get('friend_totals'):
            standings[s['id']] = rank_friends(data['friend_totals'])
    write('seasons', 'seasons.html', seasons=seasons, season_standings=standings)

    for s in seasons:
        data = load_season_data(s['id'])
        sorted_friends = rank_friends(data.get('friend_totals') or {})
        write(f"seasons/{s['id']}", 'season_detail.html',
              season=data, season_id=s['id'], sorted_friends=sorted_friends,
              team_breakdown=build_team_breakdown(sorted_friends, data.get('team_stats') or {}))


def page_all_time():
    all_time_records, season_results = {}, []
    for info in sorted(get_all_seasons(), key=lambda s: s['id']):
        data = load_season_data(info['id'])
        if not data or not data.get('friend_totals'):
            continue
        standings = []
        for rank, (friend, stats) in enumerate(rank_friends(data['friend_totals'], exclude_undrafted=True), 1):
            wins, losses = stats.get('total_wins', 0), stats.get('total_losses', 0)
            total = wins + losses
            rec = all_time_records.setdefault(friend, {
                'wins': 0, 'losses': 0, 'seasons': 0, 'titles': 0,
                'best_finish': 999, 'worst_finish': 0, 'season_history': []})
            rec['wins'] += wins
            rec['losses'] += losses
            rec['seasons'] += 1
            rec['best_finish'] = min(rec['best_finish'], rank)
            rec['worst_finish'] = max(rec['worst_finish'], rank)
            rec['titles'] += rank == 1
            row = {'season': info['display_name'], 'wins': wins, 'losses': losses,
                   'win_pct': wins / total if total else 0, 'rank': rank}
            rec['season_history'].append(row)
            standings.append({'friend': friend, **row})
        season_results.append({'season': info['display_name'], 'season_id': info['id'],
                               'winner': info.get('winner', ''), 'standings': standings})
    for rec in all_time_records.values():
        total = rec['wins'] + rec['losses']
        rec['win_pct'] = rec['wins'] / total if total else 0
    write('all-time', 'all_time.html',
          all_time=sorted(all_time_records.items(), key=lambda x: x[1]['win_pct'], reverse=True),
          season_results=season_results, total_seasons=len(season_results))


def main():
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    os.makedirs(DIST_DIR)
    open(os.path.join(DIST_DIR, '.nojekyll'), 'w').close()
    print("Building site → dist/")
    page_index()
    page_seasons()
    page_all_time()
    print("✅ Done")


if __name__ == '__main__':
    main()
