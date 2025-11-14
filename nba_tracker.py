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


def fetch_team_stats():
    """
    Fetch additional team statistics using nba_api library
    """
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Use nba_api library which is more reliable
            time.sleep(0.6)  # Rate limiting
            
            # Filter to regular season only (Oct 21, 2025 - Apr 12, 2026)
            stats = leaguedashteamstats.LeagueDashTeamStats(
                season='2025-26',
                season_type_all_star='Regular Season',
                per_mode_detailed='Totals',  # Use Totals to get cumulative stats
                date_from_nullable='10/21/2025',
                date_to_nullable='04/12/2026',
                timeout=60  # Increased timeout to 60 seconds
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
            
            return team_stats
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Error fetching team stats after {max_retries} attempts: {e}")
                return None


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
                # Find matching team - look for exact word matches
                matched_team = None
                for api_team_name in team_records.keys():
                    # Split into words for exact matching
                    team_words = set(team.lower().split())
                    api_words = set(api_team_name.lower().split())
                    
                    # Check if there's an exact word match
                    if team_words & api_words:  # Intersection
                        matched_team = api_team_name
                        break
                
                if matched_team and team_records[matched_team]['history']:
                    # Find the most recent game on or before this date
                    latest_wins = 0
                    latest_losses = 0
                    for record in team_records[matched_team]['history']:
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
            # Find matching team
            matched_team = None
            for api_team_name in current_stats.keys():
                if team.lower() in api_team_name.lower() or api_team_name.lower() in team.lower():
                    matched_team = api_team_name
                    break
            
            if matched_team:
                team_data = current_stats[matched_team]
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
    Fetch today's NBA games and map teams to friends
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
            
            # Build games list
            todays_games = []
            for idx, game in games_df.iterrows():
                home_id = game['HOME_TEAM_ID']
                visitor_id = game['VISITOR_TEAM_ID']
                home_name = team_map.get(home_id, 'Unknown')
                visitor_name = team_map.get(visitor_id, 'Unknown')
                game_time = game['GAME_STATUS_TEXT']
                
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
            # Try to find the team in team_data (case-insensitive partial match)
            matched_team = None
            for api_team_name in team_data.keys():
                if team.lower() in api_team_name.lower() or api_team_name.lower() in team.lower():
                    matched_team = api_team_name
                    break
            
            if matched_team:
                total_wins += team_data[matched_team].get('wins', 0)
                total_losses += team_data[matched_team].get('losses', 0)
                total_plus_minus += team_data[matched_team].get('total_plus_minus', 0)
                total_games_played += team_data[matched_team].get('games_played', 0)
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
    
    # Check if anyone else is mathematically eliminated
    # A friend is eliminated if their max possible win% < the best current win% of others
    # (they need to be able to finish first, not just beat someone)
    for friend in friend_totals:
        if friend == "Undrafted":
            continue
        
        max_win_pct = friend_totals[friend]['max_possible_win_pct']
        
        # Find the best current win% among all other friends (excluding self and Undrafted)
        best_other_pct = 0
        for other_friend in friend_totals:
            if other_friend == friend or other_friend == "Undrafted":
                continue
            
            other_current_pct = friend_totals[other_friend]['win_pct']
            best_other_pct = max(best_other_pct, other_current_pct)
        
        # Eliminated if max possible win% can't reach the current best (tie is acceptable)
        if max_win_pct < best_other_pct:
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
            # Find matching team in data
            matched_team = None
            for api_team_name in team_data.keys():
                if team.lower() in api_team_name.lower() or api_team_name.lower() in team.lower():
                    matched_team = api_team_name
                    break
            
            if matched_team:
                team_info = team_data[matched_team]
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
