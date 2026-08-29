"""
NBA Friends Draft Challenge — Flask web app.

Read-only: serves whatever is in nba_data_cache.json (written by update_data.py)
plus archived seasons under seasons/. It never fetches from ESPN itself.
"""

import json
import os

from flask import Flask, jsonify, render_template, request

from nba_tracker import (
    ALL_TEAMS,
    SEASON_DISPLAY,
    SEASON_START,
    TEAM_ASSIGNMENTS,
    calculate_friend_historical_standings,
    calculate_friend_totals,
    load_season_schedule,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, 'nba_data_cache.json')
SEASONS_DIR = os.path.join(BASE_DIR, 'seasons')

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_cached_data():
    """Current-season cache, or None if it doesn't exist / is unreadable."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading cache: {e}")
        return None
    if data.get('full_season_schedule'):
        load_season_schedule(cached_schedule=data['full_season_schedule'])
    return data


def load_season_data(season_id):
    path = os.path.join(SEASONS_DIR, season_id, 'data.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def get_all_seasons():
    """Summary rows for every archived season, newest first."""
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
    """Per-friend list of their teams' records, best team first."""
    breakdown = {}
    for friend, stats in sorted_friends:
        rows = []
        for team in stats['teams']:
            t = team_stats.get(team)
            if not t:
                continue
            gp = t.get('games_played', 0)
            pt_diff = (t.get('total_pts_scored', 0) - t.get('total_pts_allowed', 0)) / gp if gp else 0
            rows.append({
                'name': team,
                'wins': t.get('wins', 0),
                'losses': t.get('losses', 0),
                'win_pct': t.get('win_pct', 0),
                'pt_diff': pt_diff,
            })
        rows.sort(key=lambda r: r['wins'], reverse=True)
        breakdown[friend] = rows
    return breakdown


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    data = load_cached_data()
    if not data or not data.get('friend_totals'):
        return render_template(
            'index.html',
            season_display=SEASON_DISPLAY,
            season_start=SEASON_START,
            sorted_friends=[],
            team_breakdown={},
            last_updated=None,
            friend_history=None,
            todays_games=[],
            yesterdays_games=[],
        )

    sorted_friends = rank_friends(data['friend_totals'])
    return render_template(
        'index.html',
        season_display=SEASON_DISPLAY,
        season_start=SEASON_START,
        sorted_friends=sorted_friends,
        team_breakdown=build_team_breakdown(sorted_friends, data['team_stats']),
        last_updated=data.get('last_updated'),
        friend_history=data.get('friend_history'),
        todays_games=data.get('todays_games', []),
        yesterdays_games=data.get('yesterdays_games', []),
    )


@app.route('/api/standings')
def api_standings():
    data = load_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 503
    return jsonify(data)


@app.route('/api/teams')
def api_teams():
    return jsonify({
        'status': 'success',
        'teams': ALL_TEAMS,
        'current_assignments': TEAM_ASSIGNMENTS,
    })


@app.route('/api/recalculate', methods=['POST'])
def api_recalculate():
    """Sandbox mode: recompute standings for hypothetical team assignments."""
    custom = (request.get_json(silent=True) or {}).get('team_assignments')
    if not custom:
        return jsonify({'status': 'error', 'message': 'No team assignments provided'}), 400

    data = load_cached_data()
    if not data or not data.get('team_stats'):
        return jsonify({'status': 'error', 'message': 'No data available'}), 503

    try:
        totals = calculate_friend_totals(data['team_stats'], assignments=custom)
        history = None
        if data.get('team_records') and data.get('dates'):
            history = calculate_friend_historical_standings(
                data['team_records'], data['dates'], assignments=custom)
        sorted_friends = rank_friends(totals)
        return jsonify({
            'status': 'success',
            'sorted_friends': sorted_friends,
            'team_breakdown': build_team_breakdown(sorted_friends, data['team_stats']),
            'friend_history': history,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/seasons')
def seasons_list():
    seasons = get_all_seasons()
    season_standings = {}
    for s in seasons:
        data = load_season_data(s['id'])
        if data and data.get('friend_totals'):
            season_standings[s['id']] = rank_friends(data['friend_totals'])
    return render_template('seasons.html', seasons=seasons, season_standings=season_standings)


@app.route('/seasons/<season_id>')
def season_detail(season_id):
    data = load_season_data(season_id)
    if not data:
        return "Season not found", 404
    sorted_friends = rank_friends(data.get('friend_totals', {}))
    return render_template(
        'season_detail.html',
        season=data,
        season_id=season_id,
        sorted_friends=sorted_friends,
        team_breakdown=build_team_breakdown(sorted_friends, data.get('team_stats', {})),
    )


@app.route('/all-time')
def all_time():
    """Cumulative records across all archived seasons."""
    all_time_records = {}
    season_results = []

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
                'best_finish': 999, 'worst_finish': 0, 'season_history': [],
            })
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

        season_results.append({
            'season': info['display_name'],
            'season_id': info['id'],
            'winner': info.get('winner', ''),
            'standings': standings,
        })

    for rec in all_time_records.values():
        total = rec['wins'] + rec['losses']
        rec['win_pct'] = rec['wins'] / total if total else 0

    return render_template(
        'all_time.html',
        all_time=sorted(all_time_records.items(), key=lambda x: x[1]['win_pct'], reverse=True),
        season_results=season_results,
        total_seasons=len(season_results),
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Serving at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
