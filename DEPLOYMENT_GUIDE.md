# 🚀 Deployment Guide - Skylark Drones Operations Coordinator

This guide provides step-by-step instructions for deploying the Drone Operations Coordinator to production platforms.

## Table of Contents
1. [Local Development](#local-development)
2. [Deployment to Railway (Backend)](#deployment-to-railway-backend)
3. [Deployment to Streamlit Cloud (Frontend)](#deployment-to-streamlit-cloud-frontend)
4. [Google Sheets Setup](#google-sheets-setup)
5. [Environment Variables](#environment-variables)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Local Development

### Prerequisites
- Python 3.8 or higher
- Git
- Virtual environment tool (venv recommended)

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/your-username/droneopsaiagent.git
cd droneopsaiagent
```

2. **Create and activate virtual environment**
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Copy environment template**
```bash
cp .env.example .env
# Edit .env with your local settings
```

5. **Run backend server**
```bash
python main.py
# Backend will start on http://localhost:8000
# API documentation at http://localhost:8000/docs
```

6. **Run frontend (new terminal)**
```bash
# Activate venv if needed
source venv/bin/activate  # macOS/Linux
# or venv\Scripts\activate  # Windows

streamlit run app.py
# Frontend will start on http://localhost:8501
```

### Testing Locally

1. **Health Check**
```bash
curl http://localhost:8000/api/health
```

2. **View API Documentation**
```
Open browser to http://localhost:8000/docs
```

3. **Access Frontend**
```
Open browser to http://localhost:8501
```

---

## Deployment to Railway (Backend)

Railway is a modern deployment platform with excellent Docker support.

### Prerequisites
- Railway account (free tier available)
- GitHub repository with code
- Procfile (already included)

### Deployment Steps

1. **Create Railway project**
   - Go to https://railway.app
   - Click "Deploy Now" → "GitHub Repo"
   - Select your repository

2. **Configure environment variables**
   - In Railway dashboard, go to Variables
   - Add the following:
   ```
   PYTHONUNBUFFERED=1
   API_BASE_URL=https://your-backend-url.railway.app
   ```

3. **Deploy**
   - Railway automatically detects Procfile
   - Builds and deploys Flask app
   - Domain assigned automatically

4. **Custom domain (optional)**
   - In Railway settings, add custom domain
   - Update DNS records

5. **Verify deployment**
```bash
curl https://your-backend-url.railway.app/api/health
```

### Updating Backend on Railway
```bash
git push origin main
# Railway automatically redeploys
```

---

## Deployment to Streamlit Cloud (Frontend)

Streamlit Cloud is the easiest way to deploy Streamlit apps.

### Prerequisites
- Streamlit Cloud account (free at streamlit.io)
- GitHub repository
- Streamlit app (app.py)

### Deployment Steps

1. **Push code to GitHub**
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

2. **Deploy to Streamlit Cloud**
   - Go to https://streamlit.io
   - Click "Deploy an app"
   - Select your GitHub repository
   - Select branch: `main`
   - Select file: `app.py`

3. **Configure secrets**
   - In Streamlit Cloud, go to "Settings" → "Secrets"
   - Add secrets.toml:
   ```toml
   API_BASE_URL = "https://your-backend-url.railway.app"
   ```

4. **View app**
   - Streamlit generates URL like `app-name.streamlit.app`
   - Share with team

### Updating Frontend on Streamlit Cloud
```bash
git push origin main
# Streamlit automatically redeploys changes
```

---

## Google Sheets Setup

### For MVP (CSV-Based)

1. **Create local CSV files**
   - Already created: `pilot_roster.csv`, `drone_fleet.csv`, `missions.csv`
   - Sync manually to Google Sheets when needed

2. **Manual sync to Google Sheets**
   - Create new Google Sheets document
   - Copy CSV data to sheets
   - Match column names exactly

### For Production (Google API)

1. **Enable Google Sheets API**
   - Go to Google Cloud Console
   - Create new project
   - Enable "Google Sheets API"
   - Enable "Google Drive API"

2. **Create Service Account**
   - In Google Cloud Console → Service Accounts
   - Create new service account
   - Download JSON key file
   - Save somewhere secure

3. **Share Google Sheet with service account**
   - Get service account email from key file
   - Open your Google Sheet
   - Share with service account email (Editor access)

4. **Update code**
```python
# In google_sheets_sync.py
SHEET_ID = "your-sheet-id-from-url"
SERVICE_ACCOUNT_KEY = "/path/to/credentials.json"
```

5. **Update requirements.txt**
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

6. **Deploy with credentials**
```bash
# For Railway, add secret:
# GOOGLE_CREDENTIALS = <contents of credentials.json>
```

---

## Environment Variables

### Backend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | 8000 | Port for FastAPI server |
| `API_BASE_URL` | http://localhost:8000 | Public URL for API |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING) |
| `PYTHONUNBUFFERED` | 1 | Ensure unbuffered output |

### Frontend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | http://localhost:8000 | Backend API URL |
| `STREAMLIT_SERVER_HEADLESS` | false | Run without UI server |
| `STREAMLIT_SERVER_PORT` | 8501 | Port for Streamlit app |

### Optional (Future Use)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | For LLM integration |
| `GOOGLE_CREDENTIALS` | - | Google service account JSON |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `SENTRY_DSN` | - | Error tracking with Sentry |

---

## Monitoring & Maintenance

### Health Checks

**Backend health endpoint:**
```bash
curl https://backend.railway.app/api/health
```

**Frontend status:**
- Check Streamlit Cloud dashboard for deployment status
- View logs in Railway dashboard

### Viewing Logs

**Railway (Backend):**
- Dashboard → Logs tab
- Real-time log streaming

**Streamlit Cloud (Frontend):**
- App settings → Logs
- Shows deployment and runtime logs

### Backup & Recovery

**CSV Data Backup:**
```bash
# Backup locally
mkdir backups
cp pilot_roster.csv backups/pilot_roster_$(date +%Y%m%d).csv
cp drone_fleet.csv backups/drone_fleet_$(date +%Y%m%d).csv
cp missions.csv backups/missions_$(date +%Y%m%d).csv

# Upload to cloud storage (optional)
aws s3 cp backups/ s3://your-bucket/backups/ --recursive
```

**Database Backup (if using PostgreSQL):**
```bash
pg_dump $DATABASE_URL > backup.sql
```

### Scaling Considerations

1. **When CSV becomes bottleneck:**
   - Migrate to PostgreSQL
   - Add Redis cache
   - Implement connection pooling

2. **When single backend instance overloaded:**
   - Enable Railway auto-scaling
   - Set up load balancer
   - Use async workers

3. **Frontend scalability:**
   - Streamlit Cloud handles automatically
   - Monitor for timeout issues
   - Optimize API calls

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list | grep -E "fastapi|uvicorn"

# Run with verbose output
python main.py --debug
```

### Frontend can't connect to backend
```bash
# Check API_BASE_URL in .env
cat .env | grep API_BASE_URL

# Test API connectivity
curl -i $API_BASE_URL/api/health

# Check CORS settings in main.py
# Should allow frontend origin
```

### CSV sync issues
```bash
# Check file permissions
ls -la pilot_roster.csv drone_fleet.csv

# Check CSV format
head pilot_roster.csv  # Should have headers

# Verify CSV paths in code
grep -n "csv_path" main.py
```

### Slow API responses
```bash
# Check Railway resource usage
# Dashboard → Deployments → Resource Monitor

# Check for N+1 queries
# Review database query logs

# Enable caching
# Add Redis to requirements.txt
```

---

## Performance Optimization

### Frontend
```python
# In app.py - Add caching
@st.cache_resource
def get_api_client():
    return requests.Session()
```

### Backend
```python
# In main.py - Add response caching
from fastapi_cache import FastAPICache
# Implement cache for expensive queries
```

### Database (if migrating from CSV)
```sql
-- Create indexes for common queries
CREATE INDEX idx_pilot_status ON pilots(status);
CREATE INDEX idx_drone_location ON drones(location);
CREATE INDEX idx_mission_project ON missions(project_id);
```

---

## Security Checklist

- [ ] Change default credentials
- [ ] Enable HTTPS everywhere
- [ ] Set up authentication/authorization
- [ ] Rotate API keys regularly
- [ ] Enable audit logging
- [ ] Set up rate limiting
- [ ] Use environment variables for secrets
- [ ] Implement input validation
- [ ] Regular security updates
- [ ] Set up monitoring alerts

---

## Support & Updates

For issues or questions:
1. Check the [README.md](README.md)
2. Review [DECISION_LOG.md](DECISION_LOG.md)
3. Check Railway/Streamlit dashboards for logs
4. Open GitHub issue with details

---

**Last updated:** February 2026
**Version:** 1.0.0
