#!/bin/bash
# NBA Standings Auto-Update Script
# This script fetches new NBA data and pushes it to GitHub

# Change to the project directory
cd /Users/nick/Documents/NBAStandings

# Fetch the latest NBA data
/usr/local/bin/python3 update_data.py

# If the data fetch was successful, commit and push
if [ $? -eq 0 ]; then
    /usr/bin/git add nba_data_cache.json
    /usr/bin/git commit -m "Auto-update NBA standings - $(date '+%Y-%m-%d %H:%M')"
    /usr/bin/git push origin main
    echo "NBA data updated and pushed successfully at $(date)"
else
    echo "Failed to fetch NBA data at $(date)"
    exit 1
fi
