#!/bin/bash

# Auto-update script for NBA standings tracker
# Runs daily to fetch latest data and push to GitHub

# Regular season end date: April 12, 2026
SEASON_END_DATE="2026-04-13"  # Day after season ends
CURRENT_DATE=$(date +%Y-%m-%d)

# Check if regular season has ended
if [[ "$CURRENT_DATE" > "$SEASON_END_DATE" ]]; then
    echo "Regular season has ended. Skipping update."
    exit 0
fi

cd /Users/nick/Documents/NBAStandings

# Run the update script
python3 update_data.py

# Check if the update was successful
if [ $? -eq 0 ]; then
    # Add and commit the updated data
    git add nba_data_cache.json
    git commit -m "Automated data update - $(date '+%Y-%m-%d %H:%M')"
    git push
    
    echo "Successfully updated and pushed NBA data"
else
    echo "Failed to update NBA data"
    exit 1
fi
