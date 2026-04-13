"""
NBA Standings Web Application
Auto-updates every day at 6 AM EDT
"""

from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import json
import os
from nba_tracker import fetch_team_stats, calculate_friend_totals, TEAM_ASSIGNMENTS, fetch_historical_standings, calculate_friend_historical_standings, load_season_schedule
import glob

app = Flask(__name__)

# Path to cache file
CACHE_FILE = 'nba_data_cache.json'
SEASON_CONFIG_FILE = 'season_config.json'
SEASONS_DIR = 'seasons'

def update_nba_data():
    """
    Fetch latest NBA data and cache it
    Only runs locally - on Render, uses pre-cached data
    """
    print(f"[{datetime.now()}] Checking for NBA data updates...")
    
    # On Render or in production, skip fetching and use cached data
    import os
    if os.environ.get('RENDER') or os.path.exists('/opt/render'):
        print(f"[{datetime.now()}] Running on Render - using pre-cached data")
        return True
    
    try:
        team_stats = fetch_team_stats()
        if team_stats:
            friend_totals = calculate_friend_totals(team_stats)
            
            # Also fetch historical data for the graph
            team_records, dates = fetch_historical_standings()
            friend_history = calculate_friend_historical_standings(team_records, dates) if team_records else None
            
            # Prepare data for caching (include team_records for sandbox mode)
            cache_data = {
                'last_updated': datetime.now().isoformat(),
                'team_stats': team_stats,
                'friend_totals': friend_totals,
                'friend_history': friend_history,
                'team_records': team_records,
                'dates': dates
            }
            
            # Save to cache file
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            print(f"[{datetime.now()}] NBA data updated successfully!")
            return True
        else:
            print(f"[{datetime.now()}] Failed to fetch NBA data")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] Error updating NBA data: {e}")
        return False


def load_cached_data():
    """
    Load NBA data from cache file
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            # Populate the season schedule module variable for H2H calculations
            if data.get('full_season_schedule'):
                load_season_schedule(cached_schedule=data['full_season_schedule'])
            return data
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    # If no cache exists, fetch fresh data
    print("No cache found, fetching fresh data...")
    update_nba_data()
    
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    
    return None


@app.route('/')
def index():
    """
    Main page displaying NBA standings
    """
    data = load_cached_data()
    
    if not data:
        return "Error loading NBA data. Please try again later.", 500
    
    # Sort friends by win percentage (descending)
    sorted_friends = sorted(
        data['friend_totals'].items(), 
        key=lambda x: x[1]['win_pct'], 
        reverse=True
    )
    
    # Prepare team breakdown data
    team_breakdown = {}
    for friend, stats in sorted_friends:
        team_records = []
        for team in stats['teams']:
            # Use exact team name matching from TEAM_ASSIGNMENTS
            if team in data['team_stats']:
                team_info = data['team_stats'][team]
                games_played = team_info.get('games_played', 1)
                pts_scored = team_info.get('total_pts_scored', 0)
                pts_allowed = team_info.get('total_pts_allowed', 0)
                pt_diff_per_game = (pts_scored - pts_allowed) / games_played if games_played > 0 else 0
                
                team_records.append({
                    'name': team,
                    'wins': team_info.get('wins', 0),
                    'losses': team_info.get('losses', 0),
                    'win_pct': team_info.get('win_pct', 0),
                    'pt_diff': pt_diff_per_game
                })
        
        # Sort by wins
        team_records.sort(key=lambda x: x['wins'], reverse=True)
        team_breakdown[friend] = team_records
    
    return render_template(
        'index.html',
        sorted_friends=sorted_friends,
        team_breakdown=team_breakdown,
        last_updated=data['last_updated'],
        friend_history=data.get('friend_history'),
        todays_games=data.get('todays_games', []),
        yesterdays_games=data.get('yesterdays_games', [])
    )


@app.route('/api/standings')
def api_standings():
    """
    API endpoint to get current standings as JSON
    """
    data = load_cached_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'Failed to load data'}), 500


@app.route('/api/update')
def api_update():
    """
    Manually trigger a data update
    """
    success = update_nba_data()
    if success:
        return jsonify({'status': 'success', 'message': 'Data updated successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update data'}), 500


@app.route('/api/recalculate', methods=['POST'])
def api_recalculate():
    """
    Recalculate standings with custom team assignments (sandbox mode)
    Accepts JSON with team assignments and returns recalculated data
    """
    try:
        custom_assignments = request.json.get('team_assignments', {})
        
        if not custom_assignments:
            return jsonify({'status': 'error', 'message': 'No team assignments provided'}), 400
        
        # Load cached data
        data = load_cached_data()
        if not data:
            return jsonify({'status': 'error', 'message': 'Failed to load cached data'}), 500
        
        # Recalculate with custom assignments
        from nba_tracker import calculate_friend_totals, calculate_friend_historical_standings
        
        # Temporarily override team assignments
        original_assignments = TEAM_ASSIGNMENTS.copy()
        TEAM_ASSIGNMENTS.clear()
        TEAM_ASSIGNMENTS.update(custom_assignments)
        
        # Recalculate friend totals with custom assignments
        custom_friend_totals = calculate_friend_totals(data['team_stats'])
        
        # Recalculate historical standings if historical data exists
        custom_friend_history = None
        if data.get('friend_history') and data.get('team_records') and data.get('dates'):
            # Use cached team records - no need to fetch from API
            try:
                custom_friend_history = calculate_friend_historical_standings(
                    data['team_records'], 
                    data['dates']
                )
            except Exception as e:
                print(f"Error calculating historical data: {e}")
                custom_friend_history = None
        
        # Restore original assignments
        TEAM_ASSIGNMENTS.clear()
        TEAM_ASSIGNMENTS.update(original_assignments)
        
        # Sort friends by win percentage (descending)
        sorted_friends = sorted(
            custom_friend_totals.items(), 
            key=lambda x: x[1]['win_pct'], 
            reverse=True
        )
        
        # Prepare team breakdown data
        team_breakdown = {}
        for friend, stats in sorted_friends:
            team_records = []
            for team in stats['teams']:
                # Use exact team name matching from TEAM_ASSIGNMENTS
                if team in data['team_stats']:
                    team_info = data['team_stats'][team]
                    games_played = team_info.get('games_played', 1)
                    pts_scored = team_info.get('total_pts_scored', 0)
                    pts_allowed = team_info.get('total_pts_allowed', 0)
                    pt_diff_per_game = (pts_scored - pts_allowed) / games_played if games_played > 0 else 0
                    
                    team_records.append({
                        'name': team,
                        'wins': team_info.get('wins', 0),
                        'losses': team_info.get('losses', 0),
                        'win_pct': team_info.get('win_pct', 0),
                        'pt_diff': pt_diff_per_game
                    })
            
            # Sort by wins
            team_records.sort(key=lambda x: x['wins'], reverse=True)
            team_breakdown[friend] = team_records
        
        return jsonify({
            'status': 'success',
            'sorted_friends': sorted_friends,
            'team_breakdown': team_breakdown,
            'friend_history': custom_friend_history
        })
        
    except Exception as e:
        print(f"Error in recalculate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/teams')
def api_teams():
    """
    Get list of all NBA teams and current assignments
    """
    data = load_cached_data()
    if not data:
        return jsonify({'status': 'error', 'message': 'Failed to load data'}), 500
    
    all_teams = sorted(list(data['team_stats'].keys()))
    
    return jsonify({
        'status': 'success',
        'teams': all_teams,
        'current_assignments': TEAM_ASSIGNMENTS
    })


def load_season_config():
    """Load the season configuration file."""
    if os.path.exists(SEASON_CONFIG_FILE):
        with open(SEASON_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'current_season': None, 'seasons': {}}


def load_season_data(season_id):
    """Load archived data for a specific season."""
    data_file = os.path.join(SEASONS_DIR, season_id, 'data.json')
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    return None


def get_all_seasons():
    """Get list of all archived seasons with summary info."""
    seasons = []
    if os.path.exists(SEASONS_DIR):
        for season_dir in sorted(os.listdir(SEASONS_DIR), reverse=True):
            data_file = os.path.join(SEASONS_DIR, season_dir, 'data.json')
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
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


@app.route('/seasons')
def seasons_list():
    """Page listing all seasons with expandable standings."""
    seasons = get_all_seasons()
    
    # Load standings for each season
    season_standings = {}
    for season_info in seasons:
        data = load_season_data(season_info['id'])
        if data and data.get('friend_totals'):
            sorted_friends = sorted(
                [(f, s) for f, s in data['friend_totals'].items()],
                key=lambda x: x[1]['win_pct'],
                reverse=True
            )
            season_standings[season_info['id']] = sorted_friends
    
    return render_template('seasons.html', seasons=seasons, season_standings=season_standings)


@app.route('/seasons/<season_id>')
def season_detail(season_id):
    """View a specific past season."""
    data = load_season_data(season_id)
    if not data:
        return "Season not found.", 404
    
    # Sort friends by win percentage
    sorted_friends = sorted(
        data['friend_totals'].items(),
        key=lambda x: x[1]['win_pct'],
        reverse=True
    )
    
    # Prepare team breakdown
    team_breakdown = {}
    for friend, stats in sorted_friends:
        team_records = []
        for team in stats.get('teams', []):
            if team in data.get('team_stats', {}):
                team_info = data['team_stats'][team]
                games_played = team_info.get('games_played', 1)
                pts_scored = team_info.get('total_pts_scored', 0)
                pts_allowed = team_info.get('total_pts_allowed', 0)
                pt_diff_per_game = (pts_scored - pts_allowed) / games_played if games_played > 0 else 0
                team_records.append({
                    'name': team,
                    'wins': team_info.get('wins', 0),
                    'losses': team_info.get('losses', 0),
                    'win_pct': team_info.get('win_pct', 0),
                    'pt_diff': pt_diff_per_game
                })
        team_records.sort(key=lambda x: x['wins'], reverse=True)
        team_breakdown[friend] = team_records
    
    return render_template(
        'season_detail.html',
        season=data,
        season_id=season_id,
        sorted_friends=sorted_friends,
        team_breakdown=team_breakdown,
    )


@app.route('/all-time')
def all_time():
    """All-time cumulative records across all seasons."""
    seasons = get_all_seasons()
    
    # Build per-friend cumulative data + per-season breakdown
    all_time_records = {}
    season_results = []  # list of {season, standings: [{friend, wins, losses, win_pct, rank}]}
    
    for season_info in sorted(seasons, key=lambda s: s['id']):
        data = load_season_data(season_info['id'])
        if not data or not data.get('friend_totals'):
            continue
        
        # Sort this season's standings
        sorted_season = sorted(
            [(f, s) for f, s in data['friend_totals'].items() if f != 'Undrafted'],
            key=lambda x: x[1]['win_pct'],
            reverse=True
        )
        
        standings = []
        for rank, (friend, stats) in enumerate(sorted_season, 1):
            wins = stats.get('total_wins', 0)
            losses = stats.get('total_losses', 0)
            total = wins + losses
            
            if friend not in all_time_records:
                all_time_records[friend] = {
                    'wins': 0, 'losses': 0, 'seasons': 0,
                    'titles': 0, 'best_finish': 999, 'worst_finish': 0,
                    'season_history': []
                }
            
            rec = all_time_records[friend]
            rec['wins'] += wins
            rec['losses'] += losses
            rec['seasons'] += 1
            rec['best_finish'] = min(rec['best_finish'], rank)
            rec['worst_finish'] = max(rec['worst_finish'], rank)
            if rank == 1:
                rec['titles'] += 1
            rec['season_history'].append({
                'season': season_info['display_name'],
                'wins': wins,
                'losses': losses,
                'win_pct': wins / total if total > 0 else 0,
                'rank': rank,
            })
            
            standings.append({
                'friend': friend,
                'wins': wins,
                'losses': losses,
                'win_pct': wins / total if total > 0 else 0,
                'rank': rank,
            })
        
        season_results.append({
            'season': season_info['display_name'],
            'season_id': season_info['id'],
            'winner': season_info.get('winner', ''),
            'standings': standings,
        })
    
    # Calculate win pct and sort
    for friend in all_time_records:
        rec = all_time_records[friend]
        total = rec['wins'] + rec['losses']
        rec['win_pct'] = rec['wins'] / total if total > 0 else 0
    
    sorted_all_time = sorted(all_time_records.items(), key=lambda x: x[1]['win_pct'], reverse=True)
    
    return render_template(
        'all_time.html',
        all_time=sorted_all_time,
        season_results=season_results,
        total_seasons=len(season_results),
    )


def start_scheduler():
    """
    Start the background scheduler for automatic updates
    """
    scheduler = BackgroundScheduler()
    
    # Schedule update every day at 6 AM EDT
    eastern = pytz.timezone('US/Eastern')
    trigger = CronTrigger(hour=6, minute=0, timezone=eastern)
    
    scheduler.add_job(
        func=update_nba_data,
        trigger=trigger,
        id='daily_nba_update',
        name='Update NBA standings at 6 AM EDT',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started! Will update NBA data daily at 6 AM EDT")
    
    return scheduler


if __name__ == '__main__':
    # Update data on startup
    print("Fetching initial NBA data...")
    update_nba_data()
    
    # Start the scheduler
    scheduler = start_scheduler()
    
    # Run the Flask app
    print("\nStarting web server...")
    
    # Get port from environment variable (for Render) or use 5001
    import os
    port = int(os.environ.get('PORT', 5001))
    
    print(f"Access the standings at: http://localhost:{port}")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\nServer stopped.")
else:
    # When running with Gunicorn, initialize on module load
    update_nba_data()
    scheduler = start_scheduler()
