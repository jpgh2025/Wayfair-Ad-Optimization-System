# Wayfair Ad Optimization System - Deployment Guide

## Quick Deploy to Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/jpgh2025/Wayfair-Ad-Optimization-System)

## Prerequisites

- Git installed locally
- GitHub account (you have this ✓)
- Heroku account (free at heroku.com)
- Docker Desktop (optional, for local testing)

## Step 1: Push to GitHub

```bash
cd "/Users/guest/Wayfair Report Downloader/wsp-optimizer"

# Add remote repository
git remote add origin https://github.com/jpgh2025/Wayfair-Ad-Optimization-System.git

# Add all files
git add .

# Commit
git commit -m "Initial commit - Wayfair Ad Optimization System"

# Push to GitHub
git push -u origin main
```

## Step 2: Deploy to Heroku (Easiest Option)

### Option A: Deploy via Heroku CLI

1. Install Heroku CLI:
   ```bash
   brew tap heroku/brew && brew install heroku
   ```

2. Login to Heroku:
   ```bash
   heroku login
   ```

3. Create app and deploy:
   ```bash
   heroku create wayfair-optimizer-jpgh
   heroku git:remote -a wayfair-optimizer-jpgh
   git push heroku main
   ```

4. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY=$(openssl rand -hex 32)
   ```

5. Open your app:
   ```bash
   heroku open
   ```

### Option B: Deploy via GitHub Integration

1. Go to [Heroku Dashboard](https://dashboard.heroku.com)
2. Click "New" → "Create new app"
3. Name: `wayfair-optimizer-jpgh`
4. Go to "Deploy" tab
5. Connect to GitHub → Search for "Wayfair-Ad-Optimization-System"
6. Enable Automatic Deploys from main branch
7. Click "Deploy Branch" for initial deployment

## Step 3: Alternative Deployment Options

### Deploy to Render.com (Free tier available)

1. Go to [Render.com](https://render.com)
2. New → Web Service
3. Connect GitHub repository
4. Settings:
   - Name: `wayfair-optimizer`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add environment variable: `SECRET_KEY`

### Deploy to Railway.app

1. Go to [Railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Select your repository
4. Railway will auto-detect and deploy

### Deploy to DigitalOcean App Platform

1. Go to [DigitalOcean](https://www.digitalocean.com)
2. Create → Apps
3. Choose GitHub repository
4. Review resources and deploy

## Step 4: Post-Deployment Setup

1. **Test the deployment:**
   - Upload small test CSV files
   - Verify optimization runs correctly
   - Download results

2. **Monitor logs:**
   ```bash
   heroku logs --tail  # For Heroku
   ```

3. **Scale if needed:**
   ```bash
   heroku ps:scale web=2  # Add more dynos
   ```

## Custom Domain (Optional)

### For Heroku:
```bash
heroku domains:add www.your-domain.com
```

### DNS Settings:
Add CNAME record pointing to your Heroku app URL

## Monitoring & Maintenance

1. **Set up alerts:**
   - Use Heroku metrics
   - Add New Relic or Datadog

2. **Regular backups:**
   - Results are temporary
   - Consider S3 for long-term storage

3. **Updates:**
   ```bash
   git pull origin main
   git push heroku main
   ```

## Troubleshooting

### If deployment fails:

1. Check logs:
   ```bash
   heroku logs --tail
   ```

2. Verify requirements.txt:
   ```bash
   pip freeze > requirements.txt
   ```

3. Check Procfile exists:
   ```bash
   echo "web: gunicorn app:app" > Procfile
   ```

## Security Notes

- Never commit .env files
- Use strong SECRET_KEY
- Enable HTTPS (automatic on Heroku)
- Regularly update dependencies

## Support

If you encounter issues:
1. Check Heroku logs
2. Verify all files are committed
3. Ensure environment variables are set

Your app will be available at:
- Heroku: https://wayfair-optimizer-jpgh.herokuapp.com
- Or your chosen platform URL