# Google Sheets Integration Setup Guide

This guide walks you through setting up real-time Google Sheets synchronization for the Drone Operations AI Agent.

## 📋 Overview

The system supports two modes:

1. **Local CSV Mode** (Default for development)
   - Data stored in `/data/` CSV files
   - No external dependencies
   - Great for local testing

2. **Google Sheets Mode** (Production)
   - Real-time sync with Google Sheets
   - Cloud-based data storage
   - Shared access and collaboration
   - Automatic updates to all connected clients

## 🔧 Prerequisites

- Google Account (personal or workspace)
- Access to Google Cloud Console
- Python environment with installed dependencies

## Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a Project** at the top
3. Click **NEW PROJECT**
4. Enter project name: `drone-ops-coordinator`
5. Click **CREATE** and wait for provisioning
6. Select your new project from the dropdown

### Step 2: Enable Google Sheets API

1. In Cloud Console, go to **APIs & Services** > **Library**
2. Search for `Google Sheets API`
3. Click on it and select **ENABLE**

**Do the same for:**
- Google Drive API (for file access)

### Step 3: Create Service Account

Service Account allows your app to authenticate without manual login.

1. In Cloud Console, go to **APIs & Services** > **Credentials**
2. Click **+ CREATE CREDENTIALS**
3. Choose **Service Account**
4. Fill in details:
   - Service Account name: `drone-ops-agent`
   - Click **CREATE AND CONTINUE**
5. Grant permissions (optional):
   - Skip optional steps
   - Click **DONE**

### Step 4: Choose Authentication Method

Your organization may have policies that restrict service account key creation. **Choose the authentication method that works for your scenario:**

#### ✅ Option A: Application Default Credentials (ADC) - Recommended

**Works immediately, no organization policy issues, most secure:**

1. **Install gcloud CLI:**
   ```bash
   # macOS with Homebrew
   brew install --cask google-cloud-sdk
   
   # Or download from:
   # https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate with your Google account:**
   ```bash
   gcloud auth application-default login
   ```
   - Opens browser for OAuth login
   - Creates credentials locally (~/.config/gcloud/)
   - No key sharing needed

3. **In your `.env` file:**
   ```env
   USE_GOOGLE_SHEETS=true
   GOOGLE_SHEETS_ID=your_spreadsheet_id
   # No GOOGLE_CREDENTIALS_PATH needed for ADC!
   ```

4. **That's it!** The application will automatically use your authenticated credentials.

**Advantages:**
- ✅ No key files to manage or secure
- ✅ Works with organization policies that block keys
- ✅ Personal account authentication (safer)
- ✅ Automatic credential refresh

---

#### 🔑 Option B: JSON Key (If Organization Allows)

If your organization hasn't blocked service account key creation:

1. In Cloud Console, go to **APIs & Services** > **Credentials**
2. Under "Service Accounts", click `drone-ops-agent`
3. Go to **KEYS** tab
4. Click **ADD KEY** > **Create new key** > **JSON**
5. Click **CREATE** - saves JSON file automatically

**Setup:**
```bash
mkdir -p credentials
cp ~/Downloads/drone-ops-agent-*.json credentials/gsheet_credentials.json
```

**In `.env`:**
```env
USE_GOOGLE_SHEETS=true
GOOGLE_SHEETS_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS_PATH=./credentials/gsheet_credentials.json
```

**⚠️ Security:**
- Add to `.gitignore`: `credentials/`, `*.json`
- Never commit credentials to git
- Rotate keys periodically

---

#### 🚫 If You See: "Organization Policy blocks key creation"

**This is actually good security!** Use **Option A (ADC)** instead.

The error means:
- Your organization enforces `iam.disableServiceAccountKeyCreation` policy
- JSON keys are disabled for security
- Use Application Default Credentials instead

**Quick fix - just use ADC:**
```bash
# No complex setup needed!
gcloud auth application-default login
# Then follow Option A steps 3-4 above
```

---

#### 🏢 Option C: Workload Identity Federation (Enterprise)

For production in Google Cloud (Cloud Run, Cloud Functions):

This is the modern standard for enterprise deployments. See [Workload Identity Federation docs](https://cloud.google.com/docs/authentication/workload-identity-federation) for setup.

Benefits:
- ✅ No key rotation needed
- ✅ Automatic credential management
- ✅ Enterprise-grade security
- ✅ Works across cloud providers

---

### Step 5: Create Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Click **+ Blank spreadsheet**
3. Name it: `DroneOps-Production`
4. Create 3 sheets (tabs) with these names:
   - `Pilots`
   - `Drones`
   - `Missions`

#### Sheet 1: Pilots

Headers:
```
pilot_id | name | skills | certifications | location | status | current_assignment | available_from
```

Example data:
```
P001 | Arjun | Mapping,Survey | DGCA | Bangalore | Available | – | 2026-02-10
P002 | Neha | Inspection,Thermal | DGCA | Mumbai | Assigned | PRJ001 | 2026-02-15
```

#### Sheet 2: Drones

Headers:
```
drone_id | model | capabilities | status | location | current_assignment | maintenance_due | battery_health
```

Example data:
```
D001 | DJI | LiDAR,RGB | Available | Bangalore | – | 2026-03-15 | 100%
D002 | Autel | Thermal | In Maintenance | Mumbai | – | 2026-02-05 | 85%
```

#### Sheet 3: Missions

Headers:
```
project_id | client | location | required_skills | required_certs | start_date | end_date | priority | status
```

Example data:
```
PRJ001 | TechCorp | Bangalore | Mapping,Survey | DGCA | 2026-02-10 | 2026-02-12 | High | Open
PRJ002 | MapSolutions | Mumbai | Inspection,Thermal | DGCA | 2026-02-15 | 2026-02-18 | Medium | Open
```

### Step 6: Share Google Sheet (If Using Service Account)

**Skip this if using Option A (ADC) - no sharing needed!**

**If using Option B (JSON Key):**

1. Open your Google Sheet: `DroneOps-Production`
2. Click **Share** button
3. Get service account email from JSON credentials file:
   - Open `credentials/gsheet_credentials.json`
   - Find `"client_email": "xxxxx@xxxxx.iam.gserviceaccount.com"`
4. Paste the email in share dialog
5. Give **Editor** access
6. Click **Share**

**If using Option A (ADC):**
- No sharing needed
- Your personal account has access automatically

### Step 7: Get Sheet ID

1. Open your Google Sheet in browser
2. In the URL bar, find:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   ```
3. **Copy the `SHEET_ID_HERE` part** (long alphanumeric string)

### Step 8: Configure Application

#### For Option A (ADC) - Recommended:

```bash
# 1. Create .env from template
cp .env.example .env

# 2. Edit .env with your Sheet ID
# USE_GOOGLE_SHEETS=true
# GOOGLE_SHEETS_ID=your_sheet_id_from_step_7
# (No GOOGLE_CREDENTIALS_PATH needed)

# 3. That's it! ADC credentials are already authenticated
```

#### For Option B (JSON Key):

```bash
# 1. Move JSON credentials file
mkdir -p credentials
cp ~/Downloads/drone-ops-agent-*.json credentials/gsheet_credentials.json

# 2. Create .env from template
cp .env.example .env

# 3. Edit .env with your details
```

**In `.env`:**
```env
# Enable Google Sheets integration
USE_GOOGLE_SHEETS=true

# Your Google Sheet ID from Step 7
GOOGLE_SHEETS_ID=your_sheet_id_here

# Path to JSON credentials file
GOOGLE_CREDENTIALS_PATH=./credentials/gsheet_credentials.json
```

### Step 9: Test Connection

1. Install/update dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start backend:
   ```bash
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. Check sync status:
   ```bash
   curl http://localhost:8000/api/sync/status
   ```

   Expected response:
   ```json
   {
     "google_sheets_enabled": true,
     "google_sheets_id": "your_sheet_id",
     "sync_log": ["✓ Google Sheets API initialized"],
     "last_sync": "✓ Google Sheets API initialized"
   }
   ```

### Step 10: Sync Data

#### Manual Sync (First Time)

Sync local CSV to Google Sheets:

```bash
# Sync all data
curl -X POST http://localhost:8000/api/sync/all

# Or sync specific data type
curl -X POST http://localhost:8000/api/sync/pilots
curl -X POST http://localhost:8000/api/sync/drones
curl -X POST http://localhost:8000/api/sync/missions
```

#### Auto-Sync During Operations

Data automatically syncs when updated through the API:
- Pilot status updates sync to Sheets
- Drone status updates sync to Sheets

## 🚀 Deployment

### On Streamlit Cloud

1. Push code to GitHub (without credentials folder)
2. Deploy frontend to Streamlit Cloud
3. In Streamlit settings, add secrets (equivalent to .env):
   - Go to **App settings** > **Secrets**
   - Add your environment variables

### On Railway

1. Deploy backend to Railway
2. Add environment variables in Railway dashboard:
   - `USE_GOOGLE_SHEETS=true`
   - `GOOGLE_SHEETS_ID=your_id`
   - `GOOGLE_CREDENTIALS_PATH=/path/in/railway`
3. Upload credentials JSON as environment variable or secret file

## 📡 API Endpoints

### Check Sync Status
```bash
GET /api/sync/status
```

### Sync Operations
```bash
# Sync all data
POST /api/sync/all

# Sync specific data types
POST /api/sync/pilots
POST /api/sync/drones
POST /api/sync/missions

# Reload data from Sheets
POST /api/sync/reload
```

## 🔍 Monitoring Sync

Check sync logs in the application:

**Frontend** (Streamlit)
- Go to **Dashboard** to see sync status
- Check **System Alerts** for sync issues

**Backend** (API)
```bash
curl http://localhost:8000/api/sync/status | jq .sync_log
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `google_sheets_enabled: false` | Check `USE_GOOGLE_SHEETS=true` in .env |
| `No such file` for credentials | Verify path in `GOOGLE_CREDENTIALS_PATH` |
| Sheet ID not found | Double-check Sheet ID from URL |
| Permission denied error | Service account not shared with editor access |
| Data not syncing | Verify sheet names match (Pilots, Drones, Missions) |
| `Quota exceeded` | Wait 1 hour before retrying (API rate limit) |

### Debug Mode

Enable verbose logging:

```bash
# Check backend logs
tail -f logs/droneops.log

# Check sync operation details
curl -s http://localhost:8000/api/sync/status | python -m json.tool
```

## 🔐 Security Best Practices

1. **Never commit credentials**: Add `credentials/` to `.gitignore`
2. **Use environment variables**: Load paths from .env
3. **Rotate keys regularly**: Delete old keys, create new ones
4. **Restrict sheet access**: Share only with necessary service accounts
5. **Monitor activity**: Check Google Sheet version history

## 📚 Additional Resources

- [Google Sheets API Docs](https://developers.google.com/sheets/api)
- [Google Auth Documentation](https://cloud.google.com/docs/authentication)
- [Streamlit Secrets Management](https://docs.streamlit.io/develop/concepts/connections/secrets-management)
- [Railway Environment Variables](https://docs.railway.app/guides/environment-variables)

## ✅ Checklist

- [ ] Google Cloud Project created
- [ ] Sheets API enabled
- [ ] Drive API enabled
- [ ] Service Account created
- [ ] JSON key downloaded
- [ ] Google Sheet created with 3 sheets
- [ ] Service account shared with editor access
- [ ] Sheet ID copied
- [ ] Credentials file saved to `credentials/` folder
- [ ] `.env` updated with Sheet ID and credentials path
- [ ] `USE_GOOGLE_SHEETS=true` set in `.env`
- [ ] Backend started successfully
- [ ] Sync status shows `google_sheets_enabled: true`
- [ ] Initial data synced to Google Sheet
- [ ] Updates reflected in real-time

---

**Need Help?**
- Check logs: `curl http://localhost:8000/api/sync/status`
- Review sync details: Check API response messages
- Verify sheet structure: Ensure column headers match expected format
