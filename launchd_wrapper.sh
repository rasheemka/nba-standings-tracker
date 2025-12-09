#!/bin/bash

# Change to the project directory
cd /Users/nick/Documents/NBAStandings

# Source the shell profile to get the correct PATH
source ~/.zshrc 2>/dev/null || true

# Run the update script
bash auto_update.sh >> /Users/nick/Documents/NBAStandings/update.log 2>> /Users/nick/Documents/NBAStandings/update_error.log
