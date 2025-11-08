# NBA Friends Draft Challenge - Web App

## 🎉 Your web app is now running!

**Access the standings at:** http://localhost:5001

## Features

✅ **Beautiful responsive web interface** with gradient design and medal icons  
✅ **Automatic daily updates** at 6:00 AM EDT  
✅ **Manual refresh button** to get latest data anytime  
✅ **Live standings table** with rankings and win percentages  
✅ **Team breakdown section** showing each team's performance  
✅ **Data caching** for fast page loads  

## How It Works

1. **Scheduled Updates**: The app automatically fetches new NBA data every morning at 6 AM EDT
2. **Cached Data**: Results are saved to `nba_data_cache.json` for quick loading
3. **API Endpoints**: 
   - `http://localhost:5001/` - Main standings page
   - `http://localhost:5001/api/standings` - JSON API endpoint
   - `http://localhost:5001/api/update` - Manual update trigger

## Running the Server

**Start the server:**
```bash
python3 web_app.py
```

The server will:
- Fetch initial NBA data
- Start the scheduler for daily 6 AM updates
- Run on http://localhost:5001

**Stop the server:**
Press `Ctrl+C` in the terminal

## Keeping It Running 24/7

To keep the server running continuously (even when you close the terminal):

### Option 1: Using `screen` (macOS/Linux)
```bash
screen -S nba-tracker
python3 web_app.py
# Press Ctrl+A, then D to detach
# Reattach with: screen -r nba-tracker
```

### Option 2: Using `nohup`
```bash
nohup python3 web_app.py > server.log 2>&1 &
# Stop with: pkill -f web_app.py
```

### Option 3: Deploy to a Cloud Platform
- **Heroku** (free tier available)
- **PythonAnywhere** (free tier available)
- **Railway** or **Render**

## Files Created

- `web_app.py` - Flask web server with scheduler
- `templates/index.html` - Beautiful HTML/CSS template
- `nba_data_cache.json` - Cached NBA data (auto-generated)
- `requirements.txt` - Updated with Flask and APScheduler

## Command Line Version

You can still use the original command-line version:
```bash
python3 nba_tracker.py
```

---

**Current Status:** Server is running on port 5001 with automatic daily updates! 🏀
