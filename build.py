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
  /draft/                   current season's draft board + pick value
  /research/                pre-draft research: O/U lines, last season
"""

import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from draft import snake_owner
from nba_tracker import (ALL_TEAMS, CURRENT_SEASON_ID, GAMES_PER_TEAM, SEASON, SEASON_DISPLAY, SEASON_START,
                         TEAM_ASSIGNMENTS, load_season_config)

# One fixed color per person, stable across seasons (assigned by first appearance in config order).
PALETTE = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#65a30d', '#0d9488', '#9333ea']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, 'nba_data_cache.json')
SEASONS_DIR = os.path.join(BASE_DIR, 'seasons')
DIST_DIR = os.path.join(BASE_DIR, 'dist')

env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')),
                  autoescape=select_autoescape(['html']))
# "Portland Trail Blazers" -> "Trail Blazers", "LA Clippers" -> "Clippers"
env.filters['short'] = lambda team: 'Trail Blazers' if team.endswith('Trail Blazers') else team.split()[-1]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def friend_colors():
    cfg = load_season_config()
    names = []
    for season_id in sorted(cfg['seasons']):
        for name in cfg['seasons'][season_id]['team_assignments']:
            if name != 'Undrafted' and name not in names:
                names.append(name)
    colors = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}
    colors['Undrafted'] = '#9ca3af'
    return colors


FRIEND_COLORS = friend_colors()


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


def pace(t):
    """Wins projected over a full season at the current win rate, or None before any games."""
    gp = (t or {}).get('games_played', 0)
    return t['wins'] / gp * GAMES_PER_TEAM if gp else None


def build_draft(draft, lines, team_stats):
    """Board grid + per-pick and per-person value for a snake draft, or None if no order is set."""
    if not draft or not draft.get('order'):
        return None
    order, picks, rounds = draft['order'], draft['picks'], draft.get('rounds', 4)
    n = len(order)
    # Vegas rank among the teams actually drafted (1 = highest line) — compare to pick number.
    ranked = sorted((t for t in picks if t in lines), key=lambda t: -lines[t])
    vegas_rank = {t: i + 1 for i, t in enumerate(ranked)}

    all_picks = []
    for i, team in enumerate(picks):
        t = team_stats.get(team) or {}
        p = pace(t)
        line = lines.get(team)
        all_picks.append({
            'no': i + 1, 'round': i // n + 1, 'owner': snake_owner(order, i), 'team': team, 'line': line,
            'value': (i + 1) - vegas_rank[team] if team in vegas_rank else None,
            'wins': t.get('wins'), 'losses': t.get('losses'), 'pace': p,
            'vs_line': p - line if p is not None and line is not None else None,
        })

    grid = []
    for r in range(rounds):
        row = []
        for c in range(n):
            idx = r * n + (c if r % 2 == 0 else n - 1 - c)
            row.append(all_picks[idx] if idx < len(all_picks) else
                       {'no': idx + 1, 'owner': order[c], 'team': None, 'on_clock': idx == len(all_picks)})
        grid.append(row)

    people = []
    for name in order:
        mine = [p for p in all_picks if p['owner'] == name]
        paces = [p['pace'] for p in mine if p['pace'] is not None]
        people.append({
            'name': name,
            'line_total': sum(p['line'] for p in mine if p['line'] is not None),
            'pace_total': sum(paces) if paces else None,
        })
    people.sort(key=lambda x: -(x['pace_total'] if x['pace_total'] is not None else x['line_total']))

    return {'order': order, 'rounds': rounds, 'grid': grid, 'picks': all_picks, 'people': people,
            'complete': len(picks) >= n * rounds,
            'on_clock': snake_owner(order, len(picks)) if len(picks) < n * rounds else None,
            'in_season': any(p['pace'] is not None for p in all_picks)}


def previous_season():
    """Most recent archived season other than the current one."""
    return next((s for s in get_all_seasons() if s['id'] != CURRENT_SEASON_ID), None)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def write(rel_path, template, **ctx):
    """Render template to dist/<rel_path>/index.html with `root` pointing back to site root."""
    depth = len([p for p in rel_path.split('/') if p])
    ctx['root'] = '/'.join(['..'] * depth) if depth else '.'
    ctx['friend_colors'] = FRIEND_COLORS
    out_dir = os.path.join(DIST_DIR, rel_path)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'index.html'), 'w') as f:
        f.write(env.get_template(template).render(**ctx))
    print(f"  {rel_path or '/':<24} ← {template}")


def page_index():
    data = load_json(CACHE_FILE) or {}
    team_stats = data.get('team_stats') or {}
    sorted_friends = rank_friends(data.get('friend_totals') or {})
    write('', 'index.html', page='current',
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


def page_draft():
    data = load_json(CACHE_FILE) or {}
    write('draft', 'draft.html', page='draft', season_display=SEASON_DISPLAY, season_start=SEASON_START,
          win_totals=SEASON.get('win_totals'),
          draft=build_draft(SEASON.get('draft'), (SEASON.get('win_totals') or {}).get('lines', {}),
                            data.get('team_stats') or {}))


def page_research():
    wt = SEASON.get('win_totals') or {}
    lines = wt.get('lines', {})
    prev = previous_season()
    prev_data = load_season_data(prev['id']) if prev else {}
    prev_stats = prev_data.get('team_stats') or {}
    prev_owner = {t: f for f, ts in (prev_data.get('team_assignments') or {}).items() for t in ts}
    draft = SEASON.get('draft') or {}
    pick_no = {t: i + 1 for i, t in enumerate(draft.get('picks', []))}
    owner = {t: f for f, ts in TEAM_ASSIGNMENTS.items() for t in ts} if draft.get('picks') else {}

    rows = []
    for team in ALL_TEAMS:
        t = prev_stats.get(team) or {}
        gp = t.get('games_played', 0)
        rows.append({
            'team': team, 'line': lines.get(team),
            'prev_w': t.get('wins'), 'prev_l': t.get('losses'),
            'prev_diff': (t.get('total_pts_scored', 0) - t.get('total_pts_allowed', 0)) / gp if gp else None,
            'change': lines[team] - t['wins'] if team in lines and 'wins' in t else None,
            'prev_owner': prev_owner.get(team),
            'owner': owner.get(team) if owner.get(team) != 'Undrafted' else None,
            'pick': pick_no.get(team),
        })
    rows.sort(key=lambda r: -(r['line'] or 0))
    write('research', 'research.html', page='research', season_display=SEASON_DISPLAY,
          source=wt.get('source'), prev=prev, rows=rows, drafted=bool(owner))


def page_seasons():
    seasons = get_all_seasons()
    standings = {}
    for s in seasons:
        data = load_season_data(s['id'])
        if data and data.get('friend_totals'):
            standings[s['id']] = rank_friends(data['friend_totals'])
    write('seasons', 'seasons.html', page='seasons', seasons=seasons, season_standings=standings)

    for s in seasons:
        data = load_season_data(s['id'])
        sorted_friends = rank_friends(data.get('friend_totals') or {})
        write(f"seasons/{s['id']}", 'season_detail.html', page='seasons',
              season=data, season_id=s['id'], sorted_friends=sorted_friends,
              team_breakdown=build_team_breakdown(sorted_friends, data.get('team_stats') or {}),
              draft=build_draft(data.get('draft'), (data.get('win_totals') or {}).get('lines', {}),
                                data.get('team_stats') or {}))


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
    write('all-time', 'all_time.html', page='alltime',
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
    page_draft()
    page_research()
    print("✅ Done")


if __name__ == '__main__':
    main()
