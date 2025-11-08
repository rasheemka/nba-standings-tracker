# NBA Friends Draft Challenge Tracker

Track wins and stats for your NBA draft challenge where 7 friends each drafted 4 teams.

## Current Standings (as of last run)
1. **Adam** - 188 wins (Nuggets, Celtics, Heat, Kings)
2. **Duke** - 170 wins (Knicks, Clippers, Raptors, Bulls)
3. **JJ** - 167 wins (Thunder, Spurs, Pistons, Pelicans)
4. **Nate** - 165 wins (Magic, Hawks, Grizzlies, Suns)
5. **Nick** - 161 wins (Rockets, Timberwolves, 76ers, Trail Blazers)
6. **Chris** - 156 wins (Warriors, Pacers, Mavericks, Hornets)

*Undrafted: Nets, Jazz*

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the tracker to get current standings:
```bash
python3 nba_tracker.py
```

The script will:
- Fetch live NBA standings and stats from the NBA Stats API
- Calculate total wins for each person
- Display overall rankings
- Show individual team performance breakdowns

## Features

- **Live Data**: Pulls real-time stats from stats.nba.com
- **Complete Stats**: Shows wins, losses, win percentage, and points per game
- **Team Breakdown**: See which specific teams are performing well/poorly
- **No API Key Required**: Uses publicly available NBA Stats API

## Data Source

Data is fetched from the official NBA Stats API (stats.nba.com) for the 2024-25 season.
