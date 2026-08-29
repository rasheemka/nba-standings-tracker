"""
NBA Friends Draft Challenge tracker.

All season-specific values (dates, ESPN season id, team assignments) live in
season_config.json. Data comes exclusively from ESPN's public API.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEASON_CONFIG_FILE = os.path.join(BASE_DIR, 'season_config.json')

ESPN_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_TEAM_SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule"

GAMES_PER_TEAM = 82

# ESPN team displayName -> ESPN team ID
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
ALL_TEAMS = sorted(ESPN_TEAM_IDS)


# ---------------------------------------------------------------------------
# Season configuration
# ---------------------------------------------------------------------------

def load_season_config() -> dict:
    with open(SEASON_CONFIG_FILE) as f:
        return json.load(f)


def current_season() -> dict:
    """Return the config block for the current season, with its id under 'id'."""
    cfg = load_season_config()
    season_id = cfg['current_season']
    season = dict(cfg['seasons'][season_id])
    season['id'] = season_id
    return season


SEASON = current_season()
CURRENT_SEASON_ID: str = SEASON['id']
SEASON_DISPLAY: str = SEASON.get('display_name', CURRENT_SEASON_ID)
SEASON_START: str = SEASON['start_date']          # 'YYYY-MM-DD'
SEASON_END: str = SEASON['end_date']              # 'YYYY-MM-DD'
ESPN_SEASON_YEAR: int = SEASON['espn_season_year']
TEAM_ASSIGNMENTS: Dict[str, List[str]] = SEASON['team_assignments']


def team_to_friend_map(assignments: Optional[Dict[str, List[str]]] = None) -> Dict[str, str]:
    assignments = assignments or TEAM_ASSIGNMENTS
    return {team: friend for friend, teams in assignments.items() for team in teams}


# ---------------------------------------------------------------------------
# Standings / team stats
# ---------------------------------------------------------------------------

def fetch_team_stats() -> Optional[Dict[str, dict]]:
    """Current W/L and points for all 30 teams from ESPN standings."""
    try:
        print("Fetching standings from ESPN...")
        response = requests.get(ESPN_STANDINGS_URL, timeout=15)
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
                    'total_pts_allowed': pts_against,
                }

        if len(team_stats) != 30:
            print(f"ESPN standings: expected 30 teams, got {len(team_stats)}")
            return None
        print(f"✅ ESPN standings: {len(team_stats)} teams")
        return team_stats
    except Exception as e:
        print(f"ESPN standings fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Game-by-game history (for the win% chart)
# ---------------------------------------------------------------------------

def fetch_espn_scoreboard(date_str: Optional[str] = None,
                          assignments: Optional[Dict[str, List[str]]] = None) -> List[dict]:
    """Games for a date ('YYYYMMDD'; today if None), annotated with friend ownership."""
    try:
        params = {'dates': date_str} if date_str else None
        response = requests.get(ESPN_SCOREBOARD_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        owner = team_to_friend_map(assignments)
        games = []
        for event in data.get('events', []):
            comps = event.get('competitions', [{}])[0]
            competitors = comps.get('competitors', [])
            status = event.get('status', {}).get('type', {})
            status_detail = status.get('shortDetail', 'TBD')
            is_final = status.get('completed', False)

            if len(competitors) != 2:
                continue
            # ESPN: competitors[0] is home, competitors[1] is away
            home_team = competitors[0].get('team', {}).get('displayName', 'Unknown')
            away_team = competitors[1].get('team', {}).get('displayName', 'Unknown')
            games.append({
                'visitor': away_team,
                'home': home_team,
                'visitor_score': int(competitors[1].get('score', 0)) if is_final else None,
                'home_score': int(competitors[0].get('score', 0)) if is_final else None,
                'time': status_detail,
                'visitor_friend': owner.get(away_team),
                'home_friend': owner.get(home_team),
                'is_final': is_final,
            })
        return games
    except Exception as e:
        print(f"ESPN scoreboard fetch failed ({date_str}): {e}")
        return []


def fetch_todays_games_espn() -> List[dict]:
    return fetch_espn_scoreboard(datetime.now().strftime('%Y%m%d'))


def fetch_yesterdays_games_espn() -> List[dict]:
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    return [g for g in fetch_espn_scoreboard(yesterday) if g.get('is_final')]


def update_historical_from_espn(team_records: Optional[dict], dates: Optional[list]):
    """
    Incrementally extend per-team W/L history with every completed day since the
    last cached date (or since SEASON_START for a fresh season), up to yesterday
    and never past SEASON_END. Returns (team_records, dates).
    """
    team_records = team_records or {}
    dates = dates or []

    if dates:
        current = datetime.strptime(dates[-1], '%Y-%m-%d') + timedelta(days=1)
    else:
        current = datetime.strptime(SEASON_START, '%Y-%m-%d')
        print(f"  No cached history — bootstrapping from {SEASON_START}")

    stop = min(datetime.now().date(), datetime.strptime(SEASON_END, '%Y-%m-%d').date() + timedelta(days=1))
    added = 0
    while current.date() < stop:
        date_iso = current.strftime('%Y-%m-%d')
        print(f"  Fetching results for {date_iso}...")
        completed = [g for g in fetch_espn_scoreboard(current.strftime('%Y%m%d')) if g.get('is_final')]

        if completed:
            dates.append(date_iso)
            added += 1
            for game in completed:
                home_won = (game['home_score'] or 0) > (game['visitor_score'] or 0)
                for team_name, won in ((game['home'], home_won), (game['visitor'], not home_won)):
                    rec = team_records.setdefault(team_name, {'wins': 0, 'losses': 0, 'history': []})
                    rec['wins' if won else 'losses'] += 1
                    total = rec['wins'] + rec['losses']
                    rec['history'].append({
                        'date': date_iso,
                        'wins': rec['wins'],
                        'losses': rec['losses'],
                        'win_pct': rec['wins'] / total if total else 0,
                    })
        current += timedelta(days=1)
        time.sleep(0.3)  # be nice to ESPN

    print(f"  Added {added} new dates to historical data (total {len(dates)})")
    return team_records, dates


def calculate_friend_historical_standings(team_records, dates,
                                          assignments: Optional[Dict[str, List[str]]] = None):
    """Win% over time for each friend, derived from per-team history."""
    if not team_records or not dates:
        return None
    assignments = assignments or TEAM_ASSIGNMENTS

    friend_history = {}
    for friend, teams in assignments.items():
        series = []
        for date in dates:
            total_wins = total_losses = 0
            for team in teams:
                history = team_records.get(team, {}).get('history', [])
                latest = None
                for record in history:
                    if record['date'] <= date:
                        latest = record
                    else:
                        break
                if latest:
                    total_wins += latest['wins']
                    total_losses += latest['losses']
            games = total_wins + total_losses
            series.append({'date': date, 'win_pct': (total_wins / games * 100) if games else 0})
        friend_history[friend] = series
    return friend_history


# ---------------------------------------------------------------------------
# Full season schedule (for head-to-head elimination math)
# ---------------------------------------------------------------------------

_full_season_schedule: Optional[list] = None


def load_season_schedule(cached_schedule=None):
    """Return the season schedule, using the cached copy if given, else fetching from ESPN once."""
    global _full_season_schedule
    if _full_season_schedule is not None:
        return _full_season_schedule
    if cached_schedule:
        _full_season_schedule = cached_schedule
        return _full_season_schedule
    print("Fetching full season schedule from ESPN (one-time)...")
    return _fetch_season_schedule_from_espn()


def _fetch_season_schedule_from_espn() -> list:
    """All regular-season games for every assigned team as {date, home, away}."""
    global _full_season_schedule
    try:
        all_games, seen = [], set()
        assigned = {t for teams in TEAM_ASSIGNMENTS.values() for t in teams}

        for team_name in sorted(assigned):
            espn_id = ESPN_TEAM_IDS.get(team_name)
            if not espn_id:
                print(f"  ⚠️  No ESPN ID for {team_name}")
                continue
            response = requests.get(ESPN_TEAM_SCHEDULE_URL.format(team_id=espn_id),
                                    params={'season': ESPN_SEASON_YEAR}, timeout=15)
            response.raise_for_status()

            for event in response.json().get('events', []):
                game_id = event.get('id')
                if game_id in seen:
                    continue
                seen.add(game_id)
                game_date = event.get('date', '')[:10]
                if len(game_date) != 10:
                    continue
                competitors = event.get('competitions', [{}])[0].get('competitors', [])
                if len(competitors) == 2:
                    all_games.append({
                        'date': game_date,
                        'home': competitors[0].get('team', {}).get('displayName', 'Unknown'),
                        'away': competitors[1].get('team', {}).get('displayName', 'Unknown'),
                    })
            time.sleep(0.2)

        all_games.sort(key=lambda g: g['date'])
        _full_season_schedule = all_games
        print(f"  ✅ Season schedule: {len(all_games)} games")
        return all_games
    except Exception as e:
        print(f"Error fetching season schedule from ESPN: {e}")
        return []


def get_remaining_head_to_head(assignments: Optional[Dict[str, List[str]]] = None) -> Dict[str, int]:
    """Count future games where two of the same friend's teams play each other."""
    if not _full_season_schedule:
        return {}
    owner = team_to_friend_map(assignments)
    today = datetime.now().strftime('%Y-%m-%d')
    counts: Dict[str, int] = {}
    for game in _full_season_schedule:
        if game['date'] < today:
            continue
        h, a = owner.get(game['home']), owner.get(game['away'])
        if h and h == a and h != 'Undrafted':
            counts[h] = counts.get(h, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Friend totals
# ---------------------------------------------------------------------------

def calculate_friend_totals(team_data: Dict,
                            assignments: Optional[Dict[str, List[str]]] = None) -> Dict:
    """Aggregate each friend's teams into wins/losses/pct/etc. plus elimination status."""
    assignments = assignments or TEAM_ASSIGNMENTS
    friend_totals = {}

    for friend, teams in assignments.items():
        wins = losses = games_played = 0
        plus_minus = 0.0
        for team in teams:
            t = team_data.get(team)
            if not t:
                continue
            wins += t.get('wins', 0)
            losses += t.get('losses', 0)
            plus_minus += t.get('total_plus_minus', 0)
            games_played += t.get('games_played', 0)

        total_possible = len(teams) * GAMES_PER_TEAM
        games_remaining = total_possible - games_played
        friend_totals[friend] = {
            'total_wins': wins,
            'total_losses': losses,
            'total_games': wins + losses,
            'win_pct': wins / (wins + losses) if (wins + losses) else 0,
            'point_diff_per_game': plus_minus / games_played if games_played else 0,
            'games_remaining': games_remaining,
            'max_possible_win_pct': (wins + games_remaining) / total_possible if total_possible else 0,
            'teams': teams,
            'is_eliminated': friend == 'Undrafted',
        }

    # Head-to-head games between a friend's own teams lock in exactly 1W + 1L each,
    # which lowers their ceiling by one and raises their floor by one.
    h2h = get_remaining_head_to_head(assignments)
    for friend in friend_totals:
        friend_totals[friend]['h2h_remaining'] = h2h.get(friend, 0)

    for friend, ft in friend_totals.items():
        if friend == 'Undrafted':
            continue
        max_possible = ft['total_wins'] + ft['games_remaining'] - ft['h2h_remaining']
        best_other_floor = max(
            (o['total_wins'] + o['h2h_remaining'] for name, o in friend_totals.items()
             if name not in (friend, 'Undrafted')),
            default=0,
        )
        if max_possible < best_other_floor:
            ft['is_eliminated'] = True

    return friend_totals


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    team_stats = fetch_team_stats()
    if not team_stats:
        print("Failed to fetch NBA data.")
        return
    totals = calculate_friend_totals(team_stats)
    ranked = sorted(totals.items(), key=lambda x: x[1]['win_pct'], reverse=True)

    print(f"\nNBA FRIENDS DRAFT CHALLENGE — {SEASON_DISPLAY}")
    print(f"{'#':<3} {'Friend':<12} {'W':>4} {'L':>4} {'Win%':>7} {'+/-':>7}")
    print("-" * 42)
    for rank, (friend, s) in enumerate(ranked, 1):
        print(f"{rank:<3} {friend:<12} {s['total_wins']:>4} {s['total_losses']:>4} "
              f"{s['win_pct']:>7.3f} {s['point_diff_per_game']:>+7.1f}")

    print()
    for friend, s in ranked:
        print(f"{friend}:")
        for team in sorted(s['teams'], key=lambda t: team_stats.get(t, {}).get('wins', 0), reverse=True):
            t = team_stats.get(team, {})
            print(f"   {team:<26} {t.get('wins', 0):>3}-{t.get('losses', 0):<3}")


if __name__ == "__main__":
    main()
