# Jumbros Basketball Challenge

Standings tracker for a friends' NBA draft pool: each person drafts 4 teams and
the most regular-season wins takes the title. Live at
https://nba-standings-tracker.onrender.com.

## How it works

```
launchd (6:00 & 14:00 daily) ─▶ auto_update.sh ─▶ update_data.py ─▶ nba_data_cache.json
                                                        │                     │
                                                   ESPN public API       git commit + push
                                                                              │
                                                                     Render redeploys ─▶ web_app.py (Flask, read-only)
```

- **`season_config.json`** — the single source of truth for the current season:
  dates, ESPN season id, and who drafted which teams.
- **`nba_tracker.py`** — ESPN fetching + standings/elimination math. Reads `season_config.json`.
- **`update_data.py`** — refreshes `nba_data_cache.json` (standings, game-by-game
  history for the chart, today's/yesterday's games, season schedule).
- **`web_app.py`** — Flask app. Serves the cache and archived seasons; never calls ESPN.
- **`seasons/<id>/data.json`** — archived seasons (feeds `/seasons` and `/all-time`).
- **`new_season.py`** — rolls over to a new season (see below).

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 update_data.py      # optional: pull fresh data
python3 web_app.py          # http://localhost:5001
```

Routes: `/`, `/seasons`, `/seasons/<id>`, `/all-time`, `/api/standings`, `/api/teams`,
`POST /api/recalculate` (sandbox "what-if" mode on the home page — client-side only, nothing is saved).

## Starting a new season

1. After the draft, run (dates = first and last regular-season game days):
   ```bash
   python3 new_season.py 2026-27 --start 2026-10-20 --end 2027-04-11
   ```
   This archives the finished season to `seasons/`, adds the new season to
   `season_config.json`, and resets the cache.
2. Edit `team_assignments` for the new season in `season_config.json`.
3. Commit and push `season_config.json`, `seasons/`, `nba_data_cache.json`.

The launchd job skips itself outside the season window, so nothing else needs touching.

## Automated updates (launchd)

`com.nbastandings.update.plist` runs `auto_update.sh` at 6:00 and 14:00. To (re)install:

```bash
cp com.nbastandings.update.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.nbastandings.update 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nbastandings.update.plist
```

Logs: `update.log` / `update_error.log` in this directory (gitignored).

## Deployment

Render, from `render.yaml`: `gunicorn web_app:app`, Python 3.12. Every push to
`main` redeploys, which is how data updates reach the site.
