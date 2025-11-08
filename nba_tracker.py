"""
NBA Standings Tracker for Friends Draft Challenge
Tracks wins and stats for 7 friends who drafted 4 NBA teams each
"""

import requests
from datetime import datetime
import pandas as pd
from typing import Dict, List

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
# Undrafted: Nets, Jazz
TEAM_ASSIGNMENTS = {
    "JJ": ["Thunder", "Spurs", "Pistons", "Pelicans"],
    "Nate": ["Magic", "Hawks", "Grizzlies", "Suns"],
    "Chris": ["Warriors", "Pacers", "Mavericks", "Hornets"],
    "Adam": ["Nuggets", "Celtics", "Heat", "Kings"],
    "Duke": ["Knicks", "Clippers", "Raptors", "Bulls"],
    "Nick": ["Rockets", "Timberwolves", "76ers", "Trail Blazers"],
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
    Fetch additional team statistics (points scored, points allowed, etc.)
    """
    try:
        url = "https://stats.nba.com/stats/leaguedashteamstats"
        params = {
            "Conference": "",
            "DateFrom": "",
            "DateTo": "",
            "Division": "",
            "GameScope": "",
            "GameSegment": "",
            "LastNGames": "0",
            "LeagueID": "00",
            "Location": "",
            "MeasureType": "Base",
            "Month": "0",
            "OpponentTeamID": "0",
            "Outcome": "",
            "PORound": "0",
            "PaceAdjust": "N",
            "PerMode": "PerGame",
            "Period": "0",
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "Season": "2025-26",
            "SeasonSegment": "",
            "SeasonType": "Regular Season",
            "ShotClockRange": "",
            "StarterBench": "",
            "TeamID": "0",
            "TwoWay": "0",
            "VsConference": "",
            "VsDivision": ""
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'Connection': 'keep-alive',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }
        
        # Try up to 3 times with increasing timeout
        for attempt in range(3):
            try:
                timeout = 15 + (attempt * 5)  # 15, 20, 25 seconds
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.Timeout:
                if attempt == 2:
                    raise
                print(f"Timeout on attempt {attempt + 1}, retrying...")
                continue
        
        team_stats = {}
        result_sets = data.get('resultSets', [])
        
        if result_sets:
            headers_list = result_sets[0].get('headers', [])
            rows = result_sets[0].get('rowSet', [])
            
            for row in rows:
                team_data = dict(zip(headers_list, row))
                team_name = team_data.get('TEAM_NAME', '')
                
                team_stats[team_name] = {
                    'games_played': team_data.get('GP', 0),
                    'wins': team_data.get('W', 0),
                    'losses': team_data.get('L', 0),
                    'win_pct': team_data.get('W_PCT', 0.0),
                    'pts_scored': team_data.get('PTS', 0.0),
                    'pts_allowed': team_data.get('OPP_PTS', 0.0) if 'OPP_PTS' in headers_list else None,
                    'plus_minus': team_data.get('PLUS_MINUS', 0.0)
                }
        
        return team_stats
        
    except Exception as e:
        print(f"Error fetching team stats: {e}")
        return None


def calculate_friend_totals(team_data: Dict) -> Dict:
    """
    Calculate total wins and stats for each friend based on their drafted teams
    """
    friend_totals = {}
    
    for friend, teams in TEAM_ASSIGNMENTS.items():
        total_wins = 0
        total_losses = 0
        total_pts_scored = 0
        total_pts_allowed = 0
        games_played = 0
        
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
                total_pts_scored += team_data[matched_team].get('pts_scored', 0) * team_data[matched_team].get('games_played', 0)
                
                pts_allowed = team_data[matched_team].get('pts_allowed', 0)
                if pts_allowed:
                    total_pts_allowed += pts_allowed * team_data[matched_team].get('games_played', 0)
                
                games_played += team_data[matched_team].get('games_played', 0)
        
        friend_totals[friend] = {
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_games': total_wins + total_losses,
            'win_pct': total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0,
            'total_pts_scored': total_pts_scored,
            'total_pts_allowed': total_pts_allowed,
            'point_differential': total_pts_scored - total_pts_allowed,
            'teams': teams
        }
    
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
