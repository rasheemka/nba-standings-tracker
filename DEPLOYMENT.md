# 🚀 Deploy NBA Standings Tracker to Render

Your app is ready to deploy! Follow these steps:

## Step 1: Push to GitHub

1. **Create a new repository on GitHub:**
   - Go to https://github.com/new
   - Name: `nba-standings-tracker` (or whatever you prefer)
   - Make it **Public** or **Private** (both work)
   - **Don't** initialize with README (you already have one)
   - Click "Create repository"

2. **Push your code to GitHub:**
   ```bash
   cd /Users/nick/Documents/NBAStandings
   git remote add origin https://github.com/YOUR_USERNAME/nba-standings-tracker.git
   git branch -M main
   git push -u origin main
   ```
   
   Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 2: Deploy to Render

1. **Go to Render:**
   - Visit https://render.com
   - Click "Get Started" or "Sign Up"
   - Sign up with your GitHub account (easiest option)

2. **Create a New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub account if prompted
   - Select your `nba-standings-tracker` repository
   - Click "Connect"

3. **Configure the Service:**
   - **Name:** `nba-standings-tracker` (or your choice)
   - **Region:** Choose closest to you
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn web_app:app`
   - **Instance Type:** Select **"Free"**

4. **Click "Create Web Service"**

## Step 3: Wait for Deployment

- Render will build and deploy your app (takes 2-5 minutes)
- You'll see build logs in real-time
- Once it says "Live", your app is running! 🎉

## Step 4: Access Your App

Your app will be available at:
```
https://nba-standings-tracker.onrender.com
```
(The exact URL will be shown in Render dashboard)

## Important Notes

### Free Tier Limitations:
- **Sleeps after 15 minutes of inactivity** - first visit after sleep takes ~30 seconds to wake up
- **750 hours/month** of runtime (plenty for this use case)
- To keep it always awake, you'd need to upgrade to paid tier ($7/month) or use a service like UptimeRobot to ping it every 10 minutes

### Scheduled Updates:
- The 6 AM EDT update will work, but only if the service is awake
- On free tier, updates happen when someone visits the page or you upgrade

### Alternative: Keep-Alive Service
You can use a free service like **UptimeRobot** or **Cron-Job.org** to ping your app every 10 minutes to keep it awake and ensure 6 AM updates run.

## Troubleshooting

**If build fails:**
- Check the logs in Render dashboard
- Make sure all files are committed and pushed to GitHub

**If app crashes:**
- Check the logs in Render dashboard
- The scheduler might have issues on first deploy - it should recover

## Local Development

To run locally:
```bash
python3 web_app.py
```

Access at: http://localhost:5001

---

## Files Added for Deployment:
- ✅ `render.yaml` - Render configuration
- ✅ `runtime.txt` - Python version specification
- ✅ `requirements.txt` - Updated with gunicorn
- ✅ `.gitignore` - Git ignore file
- ✅ Updated `web_app.py` - Works with both local and production

**Ready to deploy!** 🚀
