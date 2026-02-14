#!/bin/bash

cd "$HOME/nba-standings" || exit 1

# Check if season has ended
SEASON_END_DATE="2026-04-13"
CURRENT_DATE=$(date +%Y-%m-%d)

if [[ "$CURRENT_DATE" > "$SEASON_END_DATE" ]]; then
    echo "Season has ended. Exiting."
    exit 0
fi

# Run the Python update script
/usr/bin/python3 update_data.py

# Commit and push to GitHub
git add nba_data_cache.json
git commit -m "Automated data update - $(date +%Y-%m-%d\ %H:%M)"

# Retry push up to 3 times in case of transient network errors
MAX_RETRIES=3
RETRY_DELAY=30
for i in $(seq 1 $MAX_RETRIES); do
    if git push; then
        echo "Successfully updated and pushed NBA data"
        exit 0
    else
        echo "Push attempt $i failed. Retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    fi
done

echo "ERROR: Failed to push after $MAX_RETRIES attempts"
exit 1
