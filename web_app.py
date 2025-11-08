"""
NBA Standings Web Application
Auto-updates every day at 6 AM EDT
"""

from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import json
import os
from nba_tracker import fetch_team_stats, calculate_friend_totals, TEAM_ASSIGNMENTS

app = Flask(__name__)

# Path to cache file
CACHE_FILE = 'nba_data_cache.json'

def update_nba_data():
    """
    Fetch latest NBA data and cache it
    """
    print(f"[{datetime.now()}] Updating NBA data...")
    
    try:
        team_stats = fetch_team_stats()
        if team_stats:
            friend_totals = calculate_friend_totals(team_stats)
            
            # Prepare data for caching
            cache_data = {
                'last_updated': datetime.now().isoformat(),
                'team_stats': team_stats,
                'friend_totals': friend_totals
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
                return json.load(f)
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
    
    # Sort friends by total wins
    sorted_friends = sorted(
        data['friend_totals'].items(), 
        key=lambda x: x[1]['total_wins'], 
        reverse=True
    )
    
    # Prepare team breakdown data
    team_breakdown = {}
    for friend, stats in sorted_friends:
        team_records = []
        for team in stats['teams']:
            # Find matching team in data
            matched_team = None
            for api_team_name in data['team_stats'].keys():
                if team.lower() in api_team_name.lower() or api_team_name.lower() in team.lower():
                    matched_team = api_team_name
                    break
            
            if matched_team:
                team_info = data['team_stats'][matched_team]
                team_records.append({
                    'name': team,
                    'wins': team_info.get('wins', 0),
                    'losses': team_info.get('losses', 0),
                    'win_pct': team_info.get('win_pct', 0),
                    'pts': team_info.get('pts_scored', 0)
                })
        
        # Sort by wins
        team_records.sort(key=lambda x: x['wins'], reverse=True)
        team_breakdown[friend] = team_records
    
    return render_template(
        'index.html',
        sorted_friends=sorted_friends,
        team_breakdown=team_breakdown,
        last_updated=data['last_updated']
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
