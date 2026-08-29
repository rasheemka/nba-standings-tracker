#!/bin/bash
# Twice-daily data refresh, run by launchd (com.nbastandings.update).
# Pulls fresh data from ESPN, commits the cache, and pushes so Render redeploys.

set -u
cd "$(dirname "$0")" || exit 1

# Season window comes from season_config.json; skip outside of it.
STATUS=$(python3 - <<'PY'
import json, datetime
cfg = json.load(open('season_config.json'))
s = cfg['seasons'][cfg['current_season']]
today = datetime.date.today().isoformat()
if today < s['start_date']:
    print(f"before-season {s['start_date']}")
elif today > s['end_date']:
    print(f"after-season {s['end_date']}")
else:
    print("active")
PY
)
if [[ "$STATUS" != "active" ]]; then
    echo "$(date '+%Y-%m-%d %H:%M') Skipping update: $STATUS"
    exit 0
fi

python3 update_data.py || { echo "update_data.py failed"; exit 1; }

git add nba_data_cache.json
if git diff --cached --quiet; then
    echo "No data changes."
    exit 0
fi
git commit -q -m "Automated data update - $(date '+%Y-%m-%d %H:%M')"

for i in 1 2 3; do
    if git push -q; then
        echo "$(date '+%Y-%m-%d %H:%M') Updated and pushed."
        exit 0
    fi
    echo "Push attempt $i failed; retrying in 30s..."
    sleep 30
done
echo "ERROR: push failed after 3 attempts"
exit 1
