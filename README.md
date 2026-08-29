# Jumbros Basketball Challenge

Standings tracker for a friends' NBA draft pool: each person drafts 4 teams and
the most regular-season wins takes the title. Live at
https://rasheemka.github.io/nba-standings-tracker/.

## How it works

Fully static — no server. A GitHub Actions workflow runs twice a day:

```
update_data.py ─▶ nba_data_cache.json ─▶ commit ─▶ build.py ─▶ dist/ ─▶ GitHub Pages
      │
 ESPN public API
```

- **`season_config.json`** — the single source of truth for the current season:
  dates, ESPN season id, and who drafted which teams.
- **`nba_tracker.py`** — ESPN fetching + standings/elimination math. Reads `season_config.json`.
- **`update_data.py`** — refreshes `nba_data_cache.json` (standings, game-by-game
  history for the chart, today's/yesterday's games, season schedule).
- **`build.py`** — renders `templates/` to static HTML in `dist/`. Sandbox "what-if" mode runs entirely in the browser.
- **`seasons/<id>/data.json`** — archived seasons (feeds `/seasons` and `/all-time`).
- **`new_season.py`** — rolls over to a new season (see below).

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 update_data.py                 # optional: pull fresh data
python3 build.py                       # -> dist/
python3 -m http.server -d dist 8000    # http://localhost:8000
```

Pages: `/`, `/seasons/`, `/seasons/<id>/`, `/all-time/`.

## Starting a new season

1. After the draft, run (dates = first and last regular-season game days):
   ```bash
   python3 new_season.py 2026-27 --start 2026-10-20 --end 2027-04-11
   ```
   This archives the finished season to `seasons/`, adds the new season to
   `season_config.json`, and resets the cache.
2. Edit `team_assignments` for the new season in `season_config.json`.
3. Commit and push `season_config.json`, `seasons/`, `nba_data_cache.json`.

The workflow skips data fetching outside the season window, so nothing else needs touching.

## Automated updates & deployment

`.github/workflows/update-and-deploy.yml`:
- **Scheduled** (10:00 & 18:00 UTC ≈ 6 AM / 2 PM Eastern): fetch from ESPN, commit the cache if
  it changed, build, deploy to GitHub Pages.
- **On push to `main`**: build and deploy only (no fetch).
- **Manual**: Actions tab → "Update data & deploy" → Run workflow.

GitHub disables scheduled workflows after 60 days without repo activity. If that happens
over the off-season, any push (e.g. the `new_season.py` commit) re-enables it.
