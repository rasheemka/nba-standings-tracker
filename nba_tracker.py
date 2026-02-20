"""
NBA Standings Tracker for Friends Draft Challenge
Tracks wins and stats for 7 friends who drafted 4 NBA teams each
"""

import requests
from datetime import datetime
import pandas as pd
from typing import Dict, List
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamelog
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.endpoints import ScheduleLeagueV2
import time
import csv
from io import StringIO

# NBA API uses different team names in different endpoints
# Scoreboard/GameLog APIs use "Los Angeles Clippers"
# Stats API uses "LA Clippers"
# This mapping normalizes to the stats API format (used in TEAM_ASSIGNMENTS)
API_TEAM_NAME_NORMALIZATION = {
    "Los Angeles Clippers": "LA Clippers",
    "LA Clippers": "LA Clippers",
}

def normalize_team_name(team_name):
    """Normalize team names to match TEAM_ASSIGNMENTS format"""
    return API_TEAM_NAME_NORMALIZATION.get(team_name, team_name)

# Mapping of our team names to NBA API team names
TEAM_NAME_MAP = {
    "Thunder": "Thunder",
    "Spurs": "Spurs",
    "Pistons": "Pistons",
    "Pelicans": "Pelicans",
    "Magic": "Magic",
    "Hawks": "Hawks",
    "Grizzlies": "Grizzlies",
    "Suns": "Suns",
    "Warriors": "Warriors",
    "Pacers": "Pacers",
    "Mavericks": "Mavericks",
    "Hornets": "Hornets",
    "Nuggets": "Nuggets",
    "Celtics": "Celtics",
    "Heat": "Heat",
    "Kings": "Kings",
    "Knicks": "Knicks",
    "Clippers": "Clippers",
    "Raptors": "Raptors",
    "Bulls": "Bulls",
    "Rockets": "Rockets",
    "Timberwolves": "Timberwolves",
    "76ers": "76ers",
    "Trail Blazers": "Trail Blazers"
}

# Team draft assignments - 2024-25 NBA Season
# Using full team names to match NBA API
TEAM_ASSIGNMENTS = {
    "JJ": ["Oklahoma City Thunder", "San Antonio Spurs", "Detroit Pistons", "New Orleans Pelicans"],
    "Andy": ["Cleveland Cavaliers", "Los Angeles Lakers", "Milwaukee Bucks", "Washington Wizards"],
    "Nate": ["Orlando Magic", "Atlanta Hawks", "Memphis Grizzlies", "Phoenix Suns"],
    "Chris": ["Golden State Warriors", "Indiana Pacers", "Dallas Mavericks", "Charlotte Hornets"],
    "Adam": ["Denver Nuggets", "Boston Celtics", "Miami Heat", "Sacramento Kings"],
    "Duke": ["New York Knicks", "LA Clippers", "Toronto Raptors", "Chicago Bulls"],
    "Nick": ["Houston Rockets", "Minnesota Timberwolves", "Philadelphia 76ers", "Portland Trail Blazers"],
    "Undrafted": ["Brooklyn Nets", "Utah Jazz"],
}


def fetch_nba_standings():
    """
    Fetch current NBA standings and team statistics
    Returns a dictionary with team data including wins, losses, points for/against
    """
    try:
        # Using NBA Stats API endpoint for team standings
        url = "https://stats.nba.com/stats/leaguestandingsv3"
        params = {
            "LeagueID": "00",
            "Season": "2025-26",
            "SeasonType": "Regular Season"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        standings = {}
        result_sets = data.get('resultSets', [])
        
        if result_sets:
            headers_list = result_sets[0].get('headers', [])
            rows = result_sets[0].get('rowSet', [])
            
            for row in rows:
                team_data = dict(zip(headers_list, row))
                team_name = team_data.get('TeamName', '')
                
                standings[team_name] = {
                    'team': team_name,
                    'city': team_data.get('TeamCity', ''),
                    'wins': team_data.get('WINS', 0),
                    'losses': team_data.get('LOSSES', 0),
                    'win_pct': team_data.get('WinPCT', 0.0),
                    'conf_rank': team_data.get('Conference', 0),
                    'games_back': team_data.get('ConferenceGamesBack', 0)
                }
        
        return standings
        
    except Exception as e:
        print(f"Error fetching NBA standings: {e}")
        return None


def fetch_team_stats_espn():
    """
    Primary: Fetch team standings from ESPN's public API.
    Fast and reliable.
    """
    try:
        print("Fetching from ESPN API...")
        url = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        team_stats = {}
        for conf in data.get('children', []):
            for entry in conf.get('standings', {}).get('entries', []):
                team_name = entry.get('team', {}).get('displayName', '')
                stats_map = {s['name']: s for s in entry.get('stats', [])}
                
                wins = int(float(stats_map.get('wins', {}).get('value', 0)))
                losses = int(float(stats_map.get('losses', {}).get('value', 0)))
                pts_for = float(stats_map.get('pointsFor', {}).get('value', 0))
                pts_against = float(stats_map.get('pointsAgainst', {}).get('value', 0))
                win_pct = float(stats_map.get('winPercent', {}).get('value', 0))
                
                team_stats[team_name] = {
                    'games_played': wins + losses,
                    'wins': wins,
                    'losses': losses,
                    'win_pct': win_pct,
                    'total_pts_scored': pts_for,
                    'total_plus_minus': pts_for - pts_against,
                    'total_pts_allowed': pts_against
                }
        
        if len(team_stats) == 30:
            print(f"✅ ESPN API: Got data for {len(team_stats)} teams")
            return team_stats
        else:
            print(f"ESPN API: Expected 30 teams, got {len(team_stats)}")
            return None
    except Exception as e:
        print(f"ESPN API failed: {e}")
        return None


def fetch_team_stats_nba():
    """
    Backup: Fetch team statistics from stats.nba.com via nba_api library.
    """
    max_retries = 2
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            time.sleep(1)  # Rate limiting
            
            stats = leaguedashteamstats.LeagueDashTeamStats(
                season='2025-26',
                season_type_all_star='Regular Season',
                per_mode_detailed='Totals',
                date_from_nullable='10/21/2025',
                date_to_nullable='04/12/2026',
                timeout=30
            )
            
            df = stats.get_data_frames()[0]
            
            team_stats = {}
            for _, row in df.iterrows():
                team_name = row['TEAM_NAME']
                total_pts = float(row['PTS'])
                total_plus_minus = float(row.get('PLUS_MINUS', 0.0))
                team_stats[team_name] = {
                    'games_played': int(row['GP']),
                    'wins': int(row['W']),
                    'losses': int(row['L']),
                    'win_pct': float(row['W_PCT']),
                    'total_pts_scored': total_pts,
                    'total_plus_minus': total_plus_minus,
                    'total_pts_allowed': total_pts - total_plus_minus
                }
            
            print(f"✅ NBA API: Got data for {len(team_stats)} teams")
            return team_stats
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"NBA API attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"NBA API failed after {max_retries} attempts: {e}")
                return None


def fetch_team_stats():
    """
    Fetch team statistics. Tries ESPN first (fast), falls back to NBA stats API.
    """
    # Try ESPN first (fast and reliable)
    result = fetch_team_stats_espn()
    if result:
        return result
    
    # Fall back to NBA stats API
    print("ESPN failed, trying NBA stats API as backup...")
    return fetch_team_stats_nba()


def fetch_historical_standings():
    """
    Fetch game-by-game results to build historical standings over time
    """
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            time.sleep(0.6)
            
            # Get all games for the season (regular season: Oct 21, 2025 - Apr 12, 2026)
            gamelog = leaguegamelog.LeagueGameLog(
                season='2025-26',
                season_type_all_star='Regular Season',
                date_from_nullable='10/21/2025',
                date_to_nullable='04/12/2026',
                timeout=60
            )
            
            df = gamelog.get_data_frames()[0]
            
            # Sort by game date
            df = df.sort_values('GAME_DATE')
            
            # Build cumulative records for each team by date
            team_records = {}
            dates = []
            
            for _, game in df.iterrows():
                game_date = game['GAME_DATE']
                team_name = game['TEAM_NAME']
                wl = game['WL']  # 'W' or 'L'
                
                if team_name not in team_records:
                    team_records[team_name] = {'wins': 0, 'losses': 0, 'history': []}
                
                # Update record
                if wl == 'W':
                    team_records[team_name]['wins'] += 1
                else:
                    team_records[team_name]['losses'] += 1
                
                total_games = team_records[team_name]['wins'] + team_records[team_name]['losses']
                win_pct = team_records[team_name]['wins'] / total_games if total_games > 0 else 0
                
                team_records[team_name]['history'].append({
                    'date': game_date,
                    'wins': team_records[team_name]['wins'],
                    'losses': team_records[team_name]['losses'],
                    'win_pct': win_pct
                })
                
                if game_date not in dates:
                    dates.append(game_date)
            
            return team_records, sorted(set(dates))
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Error fetching historical standings after {max_retries} attempts: {e}")
                return None, None


def calculate_friend_historical_standings(team_records, dates):
    """
    Calculate win% over time for each friend based on their teams' game-by-game records
    """
    if not team_records or not dates:
        return None
    
    friend_history = {}
    
    for friend, teams in TEAM_ASSIGNMENTS.items():
        friend_history[friend] = []
        
        for date in dates:
            total_wins = 0
            total_losses = 0
            
            for team in teams:
                # Use exact team name matching from TEAM_ASSIGNMENTS
                if team in team_records and team_records[team]['history']:
                    # Find the most recent game on or before this date
                    latest_wins = 0
                    latest_losses = 0
                    for record in team_records[team]['history']:
                        if record['date'] <= date:
                            latest_wins = record['wins']
                            latest_losses = record['losses']
                    
                    total_wins += latest_wins
                    total_losses += latest_losses
            
            total_games = total_wins + total_losses
            win_pct = (total_wins / total_games * 100) if total_games > 0 else 0
            
            friend_history[friend].append({
                'date': date,
                'win_pct': win_pct
            })
    
    return friend_history


def fetch_fivethirtyeight_projections():
    """
    Calculate simple win projections based on current performance
    Since FiveThirtyEight's API structure has changed, we'll use a simple
    pythagorean expectation model based on current stats
    """
    try:
        # We'll calculate this from current team stats instead
        # This is a placeholder - will be calculated from actual data
        print(f"  Using pythagorean expectation for projections")
        return {}
        
    except Exception as e:
        print(f"Error calculating projections: {e}")
        return None


def calculate_projected_standings(current_stats, projections):
    """
    Calculate projected final wins for each friend
    Uses pythagorean expectation: current win% applied to remaining games
    """
    if not current_stats:
        return None
    
    projected_totals = {}
    
    for friend, teams in TEAM_ASSIGNMENTS.items():
        total_projected_wins = 0
        
        for team in teams:
            # Use exact team name matching from TEAM_ASSIGNMENTS
            if team in current_stats:
                team_data = current_stats[team]
                current_wins = team_data.get('wins', 0)
                current_losses = team_data.get('losses', 0)
                games_played = current_wins + current_losses
                
                if games_played > 0:
                    # Calculate win percentage
                    win_pct = current_wins / games_played
                    
                    # Project over 82 games
                    projected_wins = win_pct * 82
                    total_projected_wins += projected_wins
        
        projected_totals[friend] = {
            'projected_wins': round(total_projected_wins, 1)
        }
    
    print(f"  Calculated projections for {len(projected_totals)} participants")
    return projected_totals


def fetch_todays_games():
    """
    Fetch today's NBA games and map teams to friends.
    Falls back to live scoreboard API if stats API hasn't populated team IDs yet.
    """
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            from datetime import datetime
            time.sleep(0.6)
            
            today = datetime.now().strftime('%m/%d/%Y')
            scoreboard = scoreboardv2.ScoreboardV2(game_date=today, timeout=60)
            games_df = scoreboard.get_data_frames()[0]
            
            if len(games_df) == 0:
                return []
            
            # Get team ID to name mapping
            all_teams = teams.get_teams()
            team_map = {team['id']: team['full_name'] for team in all_teams}
            
            # Create reverse mapping from team to friend - use exact team names from TEAM_ASSIGNMENTS
            team_to_friend = {}
            for friend, teams_list in TEAM_ASSIGNMENTS.items():
                for team in teams_list:
                    team_to_friend[team] = friend
            
            # Check if we need to use live scoreboard API as fallback
            has_null_teams = any(
                game['HOME_TEAM_ID'] is None or game['VISITOR_TEAM_ID'] is None 
                for _, game in games_df.iterrows()
            )
            
            live_games = {}
            if has_null_teams:
                # Fall back to live scoreboard API which updates earlier
                try:
                    from nba_api.live.nba.endpoints import scoreboard as live_scoreboard
                    time.sleep(0.6)
                    board = live_scoreboard.ScoreBoard()
                    games_dict = board.get_dict()
                    
                    # Index live games by position for matching
                    for idx, game in enumerate(games_dict['scoreboard']['games']):
                        away_team = game.get('awayTeam', {})
                        home_team = game.get('homeTeam', {})
                        # Build full team names (city + name)
                        away_name = f"{away_team.get('teamCity', '')} {away_team.get('teamName', '')}".strip()
                        home_name = f"{home_team.get('teamCity', '')} {home_team.get('teamName', '')}".strip()
                        status = game.get('gameStatusText', 'TBD')
                        
                        live_games[idx] = {
                            'visitor': away_name,
                            'home': home_name,
                            'time': status
                        }
                except Exception as e:
                    print(f"Live scoreboard fallback failed: {e}")
            
            # Build games list
            todays_games = []
            seen_games = set()  # Track unique games to avoid API duplicates
            
            for idx, game in games_df.iterrows():
                home_id = game['HOME_TEAM_ID']
                visitor_id = game['VISITOR_TEAM_ID']
                game_time = game['GAME_STATUS_TEXT']
                
                # Use live API data if team IDs are not populated
                if (home_id is None or visitor_id is None) and idx in live_games:
                    home_name = live_games[idx]['home']
                    visitor_name = live_games[idx]['visitor']
                    game_time = live_games[idx]['time']
                elif home_id is None or visitor_id is None:
                    # Skip games where teams are not yet determined and no fallback available
                    continue
                else:
                    home_name = team_map.get(home_id, 'Unknown')
                    visitor_name = team_map.get(visitor_id, 'Unknown')
                
                # Skip duplicate games (NBA API sometimes returns duplicates)
                game_key = f"{visitor_name}@{home_name}"
                if game_key in seen_games:
                    continue
                seen_games.add(game_key)
                
                # Normalize team names to match TEAM_ASSIGNMENTS
                home_name_normalized = normalize_team_name(home_name)
                visitor_name_normalized = normalize_team_name(visitor_name)
                
                todays_games.append({
                    'visitor': visitor_name,
                    'home': home_name,
                    'time': game_time,
                    'visitor_friend': team_to_friend.get(visitor_name_normalized, None),
                    'home_friend': team_to_friend.get(home_name_normalized, None)
                })
            
            return todays_games
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} fetching today's games failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Error fetching today's games after {max_retries} attempts: {e}")
                return []


def fetch_yesterdays_games():
    """
    Fetch yesterday's NBA games with results and map teams to friends
    Uses game log to get final scores
    """
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            from datetime import datetime, timedelta
            time.sleep(0.6)
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Get game log for yesterday
            gamelog = leaguegamelog.LeagueGameLog(
                season='2025-26',
                season_type_all_star='Regular Season',
                date_from_nullable=yesterday,
                date_to_nullable=yesterday,
                timeout=60
            )
            
            df = gamelog.get_data_frames()[0]
            
            if len(df) == 0:
                return []
            
            # Get team ID to name mapping
            all_teams = teams.get_teams()
            team_map = {team['id']: team['full_name'] for team in all_teams}
            
            # Create reverse mapping from team to friend - use exact team names from TEAM_ASSIGNMENTS
            team_to_friend = {}
            for friend, teams_list in TEAM_ASSIGNMENTS.items():
                for team in teams_list:
                    team_to_friend[team] = friend
            
            # Group by game (each game appears twice - once for each team)
            games_dict = {}
            for _, row in df.iterrows():
                game_id = row['GAME_ID']
                matchup = row['MATCHUP']
                team_name = row['TEAM_NAME']
                points = int(row['PTS'])
                wl = row['WL']
                
                if game_id not in games_dict:
                    games_dict[game_id] = {
                        'matchup': matchup,
                        'teams': []
                    }
                
                games_dict[game_id]['teams'].append({
                    'name': team_name,
                    'points': points,
                    'is_home': '@' not in matchup,  # If no @ in matchup, this team is home
                    'wl': wl
                })
            
            # Build games list with scores
            yesterdays_games = []
            for game_id, game_info in games_dict.items():
                if len(game_info['teams']) == 2:
                    # Determine which is home and which is visitor
                    team1, team2 = game_info['teams']
                    
                    if team1['is_home']:
                        home = team1
                        visitor = team2
                    else:
                        home = team2
                        visitor = team1
                    
                    # Normalize team names to match TEAM_ASSIGNMENTS
                    visitor_name_normalized = normalize_team_name(visitor['name'])
                    home_name_normalized = normalize_team_name(home['name'])
                    
                    yesterdays_games.append({
                        'visitor': visitor['name'],
                        'home': home['name'],
                        'visitor_score': visitor['points'],
                        'home_score': home['points'],
                        'visitor_friend': team_to_friend.get(visitor_name_normalized, None),
                        'home_friend': team_to_friend.get(home_name_normalized, None)
                    })
            
            return yesterdays_games
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} fetching yesterday's games failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Error fetching yesterday's games after {max_retries} attempts: {e}")
                import traceback
                traceback.print_exc()
                return []


def fetch_espn_scoreboard(date_str=None):
    """
    Fetch games from ESPN scoreboard API for a given date.
    date_str format: 'YYYYMMDD'. If None, fetches today.
    Returns list of game dicts with team names, scores, status, and friend mappings.
    """
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        if date_str:
            url += f"?dates={date_str}"
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Create reverse mapping from team to friend
        team_to_friend = {}
        for friend, teams_list in TEAM_ASSIGNMENTS.items():
            for team in teams_list:
                team_to_friend[team] = friend
        
        games = []
        for event in data.get('events', []):
            comps = event.get('competitions', [{}])[0]
            competitors = comps.get('competitors', [])
            status_detail = event.get('status', {}).get('type', {}).get('shortDetail', 'TBD')
            is_final = event.get('status', {}).get('type', {}).get('completed', False)
            
            if len(competitors) == 2:
                # ESPN: competitors[0] is home, competitors[1] is away
                home_team = competitors[0].get('team', {}).get('displayName', 'Unknown')
                away_team = competitors[1].get('team', {}).get('displayName', 'Unknown')
                home_score = int(competitors[0].get('score', 0)) if is_final else None
                away_score = int(competitors[1].get('score', 0)) if is_final else None
                
                games.append({
                    'visitor': away_team,
                    'home': home_team,
                    'visitor_score': away_score,
                    'home_score': home_score,
                    'time': status_detail,
                    'visitor_friend': team_to_friend.get(away_team, None),
                    'home_friend': team_to_friend.get(home_team, None),
                    'is_final': is_final
                })
        
        return games
    except Exception as e:
        print(f"ESPN scoreboard fetch failed: {e}")
        return []


def fetch_todays_games_espn():
    """Fetch today's games from ESPN API."""
    games = fetch_espn_scoreboard()
    # Today's games don't need scores in the display (just schedule + times)
    return games


def fetch_yesterdays_games_espn():
    """Fetch yesterday's completed games from ESPN API."""
    from datetime import timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    games = fetch_espn_scoreboard(yesterday)
    return [g for g in games if g.get('is_final')]


def update_historical_from_espn(team_records, dates):
    """
    Incrementally update team_records with any new game results from ESPN.
    Fetches recent days' scoreboards and appends W/L results for each team.
    Returns updated team_records and dates.
    """
    from datetime import timedelta
    
    if not team_records or not dates:
        print("No existing historical data to update")
        return team_records, dates
    
    last_date = dates[-1]  # e.g. '2026-02-12'
    last_dt = datetime.strptime(last_date, '%Y-%m-%d')
    today = datetime.now()
    
    # Fetch each missing day
    current = last_dt + timedelta(days=1)
    new_dates_added = 0
    
    while current.date() < today.date():
        date_espn = current.strftime('%Y%m%d')
        date_iso = current.strftime('%Y-%m-%d')
        
        print(f"  Fetching results for {date_iso}...")
        games = fetch_espn_scoreboard(date_espn)
        completed = [g for g in games if g.get('is_final')]
        
        if completed:
            dates.append(date_iso)
            new_dates_added += 1
            
            for game in completed:
                home = game['home']
                visitor = game['visitor']
                home_score = game.get('home_score', 0)
                visitor_score = game.get('visitor_score', 0)
                
                home_won = home_score > visitor_score if home_score and visitor_score else False
                
                for team_name, won in [(home, home_won), (visitor, not home_won)]:
                    if team_name not in team_records:
                        team_records[team_name] = {'wins': 0, 'losses': 0, 'history': []}
                    
                    rec = team_records[team_name]
                    if won:
                        rec['wins'] += 1
                    else:
                        rec['losses'] += 1
                    
                    total = rec['wins'] + rec['losses']
                    rec['history'].append({
                        'date': date_iso,
                        'wins': rec['wins'],
                        'losses': rec['losses'],
                        'win_pct': rec['wins'] / total if total > 0 else 0
                    })
        
        current += timedelta(days=1)
        time.sleep(0.3)  # Be nice to ESPN
    
    print(f"  Added {new_dates_added} new dates to historical data")
    return team_records, dates


# Module-level cache for the full season schedule
# List of {"date": "YYYY-MM-DD", "home": "Team Name", "away": "Team Name"} dicts
_full_season_schedule = None

# ESPN team name -> ESPN team ID mapping
ESPN_TEAM_IDS = {
    "Atlanta Hawks": 1, "Boston Celtics": 2, "Brooklyn Nets": 17,
    "Charlotte Hornets": 30, "Chicago Bulls": 4, "Cleveland Cavaliers": 5,
    "Dallas Mavericks": 6, "Denver Nuggets": 7, "Detroit Pistons": 8,
    "Golden State Warriors": 9, "Houston Rockets": 10, "Indiana Pacers": 11,
    "LA Clippers": 12, "Los Angeles Lakers": 13, "Memphis Grizzlies": 29,
    "Miami Heat": 14, "Milwaukee Bucks": 15, "Minnesota Timberwolves": 16,
    "New Orleans Pelicans": 3, "New York Knicks": 18, "Oklahoma City Thunder": 25,
    "Orlando Magic": 19, "Philadelphia 76ers": 20, "Phoenix Suns": 21,
    "Portland Trail Blazers": 22, "Sacramento Kings": 23, "San Antonio Spurs": 24,
    "Toronto Raptors": 28, "Utah Jazz": 26, "Washington Wizards": 27,
}


def load_season_schedule(cached_schedule=None):
    """
    Load or fetch the full season schedule. The schedule is fixed for the season,
    so once fetched from ESPN it's cached in the JSON file forever.
    
    cached_schedule: list from nba_data_cache.json['full_season_schedule'], or None
    Returns the full schedule list, or None if fetch fails.
    """
    global _full_season_schedule
    
    if _full_season_schedule is not None:
        return _full_season_schedule
    
    if cached_schedule:
        _full_season_schedule = cached_schedule
        print(f"Loaded cached season schedule: {len(cached_schedule)} games")
        return _full_season_schedule
    
    # No cache — fetch from ESPN (one-time operation)
    print("Fetching full season schedule from ESPN (one-time)...")
    return _fetch_season_schedule_from_espn()


def _fetch_season_schedule_from_espn() -> list:
    """
    Fetch the full 2025-26 NBA season schedule from ESPN.
    Fetches one team per friend to get all intra-friend matchups,
    plus all remaining teams to get the complete schedule.
    Returns list of {"date": "YYYY-MM-DD", "home": "...", "away": "..."} dicts.
    """
    global _full_season_schedule
    
    try:
        all_games = []
        seen_game_ids = set()
        
        # Collect all unique teams from TEAM_ASSIGNMENTS (excluding duplicates)
        all_assigned_teams = set()
        for friend, teams_list in TEAM_ASSIGNMENTS.items():
            for team in teams_list:
                all_assigned_teams.add(team)
        
        print(f"  Fetching schedules for {len(all_assigned_teams)} assigned teams...")
        
        for team_name in sorted(all_assigned_teams):
            espn_id = ESPN_TEAM_IDS.get(team_name)
            if not espn_id:
                print(f"  ⚠️  No ESPN ID for {team_name}")
                continue
            
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{espn_id}/schedule?season=2026"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            team_new = 0
            for event in data.get('events', []):
                game_id = event.get('id')
                if game_id in seen_game_ids:
                    continue
                seen_game_ids.add(game_id)
                
                # Parse date (ESPN gives ISO format like "2025-10-22T23:30Z")
                event_date_str = event.get('date', '')
                try:
                    game_date = datetime.strptime(event_date_str[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
                except (ValueError, IndexError):
                    continue
                
                comps = event.get('competitions', [{}])[0]
                competitors = comps.get('competitors', [])
                if len(competitors) == 2:
                    home_team = competitors[0].get('team', {}).get('displayName', 'Unknown')
                    away_team = competitors[1].get('team', {}).get('displayName', 'Unknown')
                    all_games.append({
                        'date': game_date,
                        'home': home_team,
                        'away': away_team,
                    })
                    team_new += 1
            
            print(f"    {team_name}: +{team_new} new games (total: {len(all_games)})")
            time.sleep(0.2)  # Be nice to ESPN
        
        # Sort by date
        all_games.sort(key=lambda g: g['date'])
        
        _full_season_schedule = all_games
        print(f"  ✅ Full season schedule: {len(all_games)} games")
        return all_games
    
    except Exception as e:
        print(f"Error fetching season schedule from ESPN: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_remaining_head_to_head() -> Dict[str, int]:
    """
    Count future games where two of the same friend's teams play each other.
    Uses the cached full-season schedule and filters to games on or after today.
    
    Returns a dict of {friend_name: number_of_intra_team_games_remaining}
    """
    if not _full_season_schedule:
        print("No season schedule available for H2H calculation")
        return {}
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Build reverse lookup: team_name -> friend
    team_to_friend = {}
    for friend, friend_teams in TEAM_ASSIGNMENTS.items():
        for team in friend_teams:
            team_to_friend[team] = friend
    
    head_to_head_counts = {}
    for game in _full_season_schedule:
        # Only count games on or after today
        if game['date'] < today_str:
            continue
        
        home_friend = team_to_friend.get(game['home'])
        away_friend = team_to_friend.get(game['away'])
        
        if (home_friend and away_friend 
                and home_friend == away_friend 
                and home_friend != 'Undrafted'):
            head_to_head_counts[home_friend] = head_to_head_counts.get(home_friend, 0) + 1
    
    print(f"Head-to-head remaining: {head_to_head_counts}")
    return head_to_head_counts


def calculate_friend_totals(team_data: Dict) -> Dict:
    """
    Calculate total wins and stats for each friend based on their drafted teams
    """
    friend_totals = {}
    
    for friend, teams in TEAM_ASSIGNMENTS.items():
        total_wins = 0
        total_losses = 0
        total_plus_minus = 0
        total_games_played = 0
        team_count = 0
        
        for team in teams:
            # Use exact team name matching from TEAM_ASSIGNMENTS
            if team in team_data:
                total_wins += team_data[team].get('wins', 0)
                total_losses += team_data[team].get('losses', 0)
                total_plus_minus += team_data[team].get('total_plus_minus', 0)
                total_games_played += team_data[team].get('games_played', 0)
                team_count += 1
        
        # Calculate games remaining (82 games per team)
        total_possible_games = len(teams) * 82
        games_remaining = total_possible_games - total_games_played
        
        # Calculate maximum possible wins (current wins + all remaining games)
        max_possible_wins = total_wins + games_remaining
        max_possible_games = total_possible_games
        max_possible_win_pct = max_possible_wins / max_possible_games if max_possible_games > 0 else 0
        
        friend_totals[friend] = {
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_games': total_wins + total_losses,
            'win_pct': total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0,
            'point_diff_per_game': total_plus_minus / total_games_played if total_games_played > 0 else 0,
            'games_remaining': games_remaining,
            'max_possible_win_pct': max_possible_win_pct,
            'teams': teams
        }
    
    # Determine elimination status
    # Undrafted is always eliminated
    for friend in friend_totals:
        if friend == "Undrafted":
            friend_totals[friend]['is_eliminated'] = True
        else:
            friend_totals[friend]['is_eliminated'] = False
    
    # Fetch remaining head-to-head games (where two of the same friend's teams play)
    # Each such game guarantees 1W + 1L, reducing max possible wins by 1
    # (because best case for two separate games is 2W, but head-to-head locks in 1W + 1L)
    # Also: the leader gets guaranteed wins from THEIR head-to-head games,
    # raising their minimum locked-in wins.
    head_to_head = get_remaining_head_to_head()
    
    # Store h2h count in each friend's data for display
    for friend in friend_totals:
        friend_totals[friend]['h2h_remaining'] = head_to_head.get(friend, 0)
    
    # Check if anyone else is mathematically eliminated
    # A friend is eliminated if, even winning ALL remaining games (accounting for
    # intra-team head-to-head matchups), they'd still have fewer total wins than
    # the leader's minimum guaranteed wins.
    for friend in friend_totals:
        if friend == "Undrafted":
            continue
        
        # Max possible wins = current wins + remaining games - head-to-head matchups
        # (each h2h game means one of those "remaining" is a guaranteed loss, not a possible win)
        h2h_penalty = friend_totals[friend]['h2h_remaining']
        max_possible_wins = friend_totals[friend]['total_wins'] + friend_totals[friend]['games_remaining'] - h2h_penalty
        
        # Find the best other friend's minimum guaranteed wins
        # Their current wins are locked in, plus they get 1 guaranteed win per h2h game
        best_other_min_wins = 0
        for other_friend in friend_totals:
            if other_friend == friend or other_friend == "Undrafted":
                continue
            
            other_guaranteed_wins = friend_totals[other_friend]['total_wins'] + friend_totals[other_friend]['h2h_remaining']
            best_other_min_wins = max(best_other_min_wins, other_guaranteed_wins)
        
        # Eliminated if max possible wins can't reach the leader's minimum guaranteed wins (tie is acceptable)
        if max_possible_wins < best_other_min_wins:
            friend_totals[friend]['is_eliminated'] = True
    
    return friend_totals


def display_standings(friend_totals: Dict):
    """
    Display the current standings for the friends draft challenge
    """
    print("\n" + "="*80)
    print("NBA FRIENDS DRAFT CHALLENGE - CURRENT STANDINGS")
    print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Sort by total wins (descending)
    sorted_friends = sorted(friend_totals.items(), key=lambda x: x[1]['total_wins'], reverse=True)
    
    print(f"{'Rank':<6} {'Friend':<15} {'Wins':<8} {'Losses':<8} {'Win %':<10} {'Pt Diff':<12}")
    print("-" * 80)
    
    for rank, (friend, stats) in enumerate(sorted_friends, 1):
        print(f"{rank:<6} {friend:<15} {stats['total_wins']:<8} {stats['total_losses']:<8} "
              f"{stats['win_pct']:.3f}    {stats['point_differential']:>10.1f}")
    
    print("\n" + "="*80)
    print("DETAILED BREAKDOWN")
    print("="*80 + "\n")
    
    for rank, (friend, stats) in enumerate(sorted_friends, 1):
        print(f"{rank}. {friend} - {stats['total_wins']} Wins")
        print(f"   Teams: {', '.join(stats['teams'])}")
        print(f"   Record: {stats['total_wins']}-{stats['total_losses']} ({stats['win_pct']:.1%})")
        print(f"   Total Points Scored: {stats['total_pts_scored']:.1f}")
        if stats['total_pts_allowed'] > 0:
            print(f"   Total Points Allowed: {stats['total_pts_allowed']:.1f}")
            print(f"   Point Differential: {stats['point_differential']:+.1f}")
        print()


def display_team_breakdown(team_data: Dict, friend_totals: Dict):
    """
    Display individual team performance for each friend
    """
    print("\n" + "="*80)
    print("INDIVIDUAL TEAM PERFORMANCE")
    print("="*80 + "\n")
    
    sorted_friends = sorted(friend_totals.items(), key=lambda x: x[1]['total_wins'], reverse=True)
    
    for rank, (friend, stats) in enumerate(sorted_friends, 1):
        print(f"{rank}. {friend} ({stats['total_wins']} total wins)")
        print("-" * 60)
        
        team_records = []
        for team in stats['teams']:
            # Use exact team name matching from TEAM_ASSIGNMENTS
            if team in team_data:
                team_info = team_data[team]
                team_records.append({
                    'name': team,
                    'wins': team_info.get('wins', 0),
                    'losses': team_info.get('losses', 0),
                    'win_pct': team_info.get('win_pct', 0),
                    'pts': team_info.get('pts_scored', 0)
                })
        
        # Sort by wins
        team_records.sort(key=lambda x: x['wins'], reverse=True)
        
        for team_rec in team_records:
            print(f"   {team_rec['name']:<20} {team_rec['wins']:>3}-{team_rec['losses']:<3} "
                  f"({team_rec['win_pct']:.3f})  {team_rec['pts']:.1f} PPG")
        print()


def main():
    """
    Main function to run the NBA standings tracker
    """
    print("Fetching NBA data...")
    
    # Fetch team statistics
    team_stats = fetch_team_stats()
    
    if not team_stats:
        print("Failed to fetch NBA data. Please try again later.")
        return
    
    print(f"Successfully fetched data for {len(team_stats)} teams\n")
    
    # Calculate totals for each friend
    friend_totals = calculate_friend_totals(team_stats)
    
    # Display standings
    display_standings(friend_totals)
    
    # Display individual team breakdown
    display_team_breakdown(team_stats, friend_totals)


if __name__ == "__main__":
    main()
