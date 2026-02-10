# Drone Operations AI Agent - Skylark Drones

A comprehensive AI-powered drone operations coordinator system for managing pilot rosters, drone inventory, mission assignments, and automated conflict detection. Built with FastAPI backend and Streamlit frontend.

## 🚀 Features

- **Pilot Roster Management**: Query pilot availability, skills, certifications, and locations
- **Drone Inventory System**: Track drone status, maintenance schedules, and capabilities
- **Mission Assignment Tracking**: Create, validate, and track mission assignments with conflict detection
- **Automated Conflict Detection**: 7-type conflict detection system (double-booking, skill mismatch, certification gaps, location conflicts, maintenance conflicts)
- **Conversational AI Interface**: Natural language agent for queries and operations
- **Urgent Reassignments**: Emergency resource reallocation with automatic drone compatibility matching
- **Decision Logging**: Comprehensive audit trail of all operations
- **Google Sheets Integration**: Real-time 2-way sync with Google Sheets for cloud-based data management

## 📋 Requirements

- Python 3.9+
- FastAPI
- Streamlit
- Pydantic
- Pandas
- Requests

## 📦 Installation

### 1. Clone/Extract the Project

```bash
cd droneopsaiagent
```

### 2. Create Virtual Environment

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**If requirements.txt doesn't exist, install manually:**

```bash
pip install fastapi uvicorn streamlit pydantic pandas requests python-multipart
```

### 4. Verify Project Structure

```
droneopsaiagent/
├── backend/
│   ├── main.py                    # FastAPI application (40+ endpoints)
│   ├── models.py                  # Pydantic data models
│   ├── conflict_detection.py      # Conflict validation engine
│   └── google_sheets_sync.py      # CSV/Google Sheets integration
├── frontend/
│   └── app.py                     # Streamlit UI (7 pages)
├── data/
│   ├── pilot_roster.csv           # Pilot database (4 pilots)
│   ├── drone_fleet.csv            # Drone inventory (4 drones)
│   └── missions.csv               # Missions/projects (3 projects)
├── README.md                       # Project documentation
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment template
```

## 🏃 Running Locally

### Option 1: Run Backend and Frontend Separately (Recommended)

**Terminal 1 - Start Backend:**

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**

```bash
cd frontend
streamlit run app.py --server.port=8501
```

**Access the application:**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Alternative API Docs: http://localhost:8000/redoc

### Option 2: Run with Shell Scripts

```bash
chmod +x setup.sh start.sh
./start.sh  # Starts both backend and frontend
```

### Option 3: Run with Make

If you have `make` installed:

```bash
make run
```

## 🛠️ Usage Guide

### Streamlit Frontend (http://localhost:8501)

The application has 7 interactive pages:

1. **Dashboard**
   - System overview and statistics
   - Alert system for issues or maintenance due

2. **Air Agent** (Conversational AI)
   - Query pilot availability: "Is Arjun available?"
   - Check drone status: "What drones are in Bangalore?"
   - Create assignments: "Create assignment for Neha"
   - Detect conflicts: "Check conflicts for PRJ001"
   - View statistics: "Show me pilot statistics"

3. **Pilot Management**
   - View all pilots with skills and certifications
   - Query specific pilot availability
   - Update pilot status (Available/Assigned/On Leave)

4. **Drone Fleet**
   - View all drones and their capabilities
   - Check maintenance schedules
   - Update drone status and maintenance information

5. **Assign Missions**
   - Create new mission assignments
   - Preview validation checks before submission
   - Review existing assignments

6. **Conflict Detection**
   - System-wide conflict scan
   - Detailed conflict reports with suggestions
   - Manual conflict check for specific assignments

7. **Urgent Reassignments**
   - Emergency pilot reassignments between projects
   - Automatic drone compatibility matching
   - Real-time validation and alerts

### API Endpoints (FastAPI)

#### Pilot Management
```bash
# Get all pilots
curl http://localhost:8000/api/pilots

# Get pilot availability
curl -X POST http://localhost:8000/api/pilots/availability \
  -H "Content-Type: application/json" \
  -d '{"pilot_name": "Arjun"}'

# Update pilot status
curl -X PUT http://localhost:8000/api/pilots/update-status \
  -H "Content-Type: application/json" \
  -d '{"pilot_name": "Arjun", "status": "On Leave", "current_assignment": null}'
```

#### Drone Management
```bash
# Get all drones
curl http://localhost:8000/api/drones

# Query drone capabilities
curl -X POST http://localhost:8000/api/drones/query \
  -H "Content-Type: application/json" \
  -d '{"capability": "Thermal", "location": "Bangalore"}'

# Check maintenance alerts
curl http://localhost:8000/api/drones/maintenance-alert
```

#### Assignments
```bash
# Validate assignment before creation
curl -X POST http://localhost:8000/api/assignments/validate \
  -H "Content-Type: application/json" \
  -d '{"pilot_name": "Arjun", "project_id": "PRJ001", "start_date": "2026-02-10", "end_date": "2026-02-12"}'

# Create assignment
curl -X POST http://localhost:8000/api/assignments/create \
  -H "Content-Type: application/json" \
  -d '{"pilot_name": "Arjun", "project_id": "PRJ001", "start_date": "2026-02-10", "end_date": "2026-02-12"}'
```

#### Operations
```bash
# Detect conflicts
curl -X POST http://localhost:8000/api/operations/conflicts/detect \
  -H "Content-Type: application/json" \
  -d '{"pilot_name": "Arjun", "project_id": "PRJ001"}'

# Get system statistics
curl http://localhost:8000/api/operations/stats

# Urgent reassignment
curl -X POST http://localhost:8000/api/reassignments/urgent \
  -H "Content-Type: application/json" \
  -d '{"pilot_name": "Arjun", "new_project_id": "PRJ002", "reason": "Emergency reallocation"}'
```

## 📂 Data Format

### Pilot Roster (CSV)
```
pilot_id,name,skills,certifications,location,status,current_assignment,available_from
P001,Arjun,"Mapping,Survey",DGCA,Bangalore,Available,,2026-02-10
P002,Neha,"Inspection,Thermal",DGCA,Mumbai,Assigned,PRJ001,2026-02-15
```

### Drone Fleet (CSV)
```
drone_id,model,capabilities,status,location,current_assignment,maintenance_due
D001,DJI,"LiDAR,RGB",Available,Bangalore,,2026-03-15
D002,Autel,Thermal,In Maintenance,Mumbai,,2026-02-05
```

### Missions (CSV)
```
project_id,client,location,required_skills,required_certs,start_date,end_date,priority,status
PRJ001,TechCorp,Bangalore,"Mapping,Survey",DGCA,2026-02-10,2026-02-12,High,Open
```

## 🚀 Deployment

### Streamlit Cloud (Frontend)

1. **Push code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/droneopsaiagent.git
   git push -u origin main
   ```

2. **Deploy to Streamlit Cloud:**
   - Visit https://share.streamlit.io
   - Click "New app"
   - Select your GitHub repository
   - Set main file path to: `frontend/app.py`
   - Click "Deploy"

3. **Update API URL:**
   - After deployment, verify `API_BASE_URL` in frontend/app.py points to production backend
   - Set to your Railway backend URL

### Railway (Backend)

1. **Create Railway account:**
   - Visit https://railway.app
   - Sign up and create new project

2. **Connect GitHub:**
   - In Railway dashboard, click "Create a New" → "GitHub Repo"
   - Select your droneopsaiagent repository

3. **Configure deployment:**
   - Click on the created service
   - Go to "Settings" tab
   - Set environment variables:
     ```
     RAILWAY_ENVIRONMENT=production
     DATABASE_URL=your_database_url (if using)
     ```

4. **Start command:**
   - In "Deploy" tab, set start command:
     ```bash
     cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
     ```

5. **Deploy:**
   - Railway auto-deploys on push to main branch
   - Copy the public URL from Railway dashboard

### Manual Deployment (VPS/Cloud Server)

1. **SSH into server:**
   ```bash
   ssh user@your_server_ip
   ```

2. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/droneopsaiagent.git
   cd droneopsaiagent
   ```

4. **Setup virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Run with Supervisor (for persistent processes):**
   
   Create `/etc/supervisor/conf.d/droneops.conf`:
   ```ini
   [program:droneops-backend]
   directory=/home/user/droneopsaiagent/backend
   command=/home/user/droneopsaiagent/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/droneops-backend.err.log
   stdout_logfile=/var/log/droneops-backend.out.log

   [program:droneops-frontend]
   directory=/home/user/droneopsaiagent/frontend
   command=/home/user/droneopsaiagent/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/droneops-frontend.err.log
   stdout_logfile=/var/log/droneops-frontend.out.log
   ```

   Then:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start droneops-backend droneops-frontend
   ```

6. **Setup Nginx reverse proxy:**
   ```nginx
   upstream backend {
       server localhost:8000;
   }
   upstream frontend {
       server localhost:8501;
   }

   server {
       listen 80;
       server_name your_domain.com;

       location /api/ {
           proxy_pass http://backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location / {
           proxy_pass http://frontend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## 🔄 Google Sheets Integration

The system supports **real-time 2-way sync** with Google Sheets for production deployments!

### Quick Start (CSV Mode - Default)

For local development, the system uses local CSV files by default:
- No setup required
- Data stored in `/data/` folder
- Perfect for testing and prototyping

### Production Setup (Google Sheets Mode)

Enable full cloud-based data synchronization:

1. **Prerequisites:**
   - Google Account
   - Google Cloud Project
   - Service Account credentials

2. **Complete Setup Guide:**
   - See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed step-by-step instructions
   - Includes screenshots and troubleshooting

3. **Quick Configuration:**

   ```bash
   # Create credentials directory
   mkdir -p credentials
   
   # Copy your service account JSON
   cp ~/Downloads/service-account-key.json credentials/gsheet_credentials.json
   
   # Update .env
   cp .env.example .env
   ```

   In `.env`:
   ```env
   USE_GOOGLE_SHEETS=true
   GOOGLE_SHEETS_ID=your_spreadsheet_id_here
   GOOGLE_CREDENTIALS_PATH=./credentials/gsheet_credentials.json
   ```

4. **Verify Connection:**
   ```bash
   curl http://localhost:8000/api/sync/status
   ```

### Available Sync Endpoints

```bash
# Check sync status
GET /api/sync/status

# Manual sync operations
POST /api/sync/all          # Sync all data
POST /api/sync/pilots       # Sync pilots only
POST /api/sync/drones       # Sync drones only
POST /api/sync/missions     # Sync missions only

# Reload data from Sheets or CSV
POST /api/sync/reload
```

### Sync Behavior

- **Automatic**: Updates made through API automatically sync to Google Sheets
- **Manual**: Use sync endpoints above for bulk operations
- **Fallback**: If Google Sheets fails, system continues using local CSV
- **Bi-directional**: Load from Google Sheets on startup or manual reload

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 already in use | `lsof -ti:8000 \| xargs kill -9` |
| Port 8501 already in use | `lsof -ti:8501 \| xargs kill -9` |
| CSV files not found | Ensure `/data/` folder exists with CSV files |
| Backend not responding | Check backend is running with `curl http://localhost:8000/api/health` |
| Frontend not loading | Wait 30 seconds for Streamlit to start, then refresh browser |
| Module import errors | Ensure you're in correct directory and virtual environment is activated |

## 📝 Solution Summary

This project solves Skylark Drones' operational coordination challenges with:

- ✅ **Automated Conflict Detection**: 7-type validation prevents double-booking and skill mismatches
- ✅ **Real-time Availability Tracking**: Instant pilot/drone status updates
- ✅ **Conversational Interface**: Natural language queries for quick decisions
- ✅ **Scalable Architecture**: FastAPI backend scales independently from Streamlit frontend
- ✅ **Audit Trail**: Complete decision logging for compliance
- ✅ **Emergency Operations**: Urgent reassignment with instant drone matching

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review API logs: Check terminal output when backend/frontend run
3. Check Streamlit logs: Look in `.streamlit/logs/` directory

## 📄 License

MIT License - See LICENSE file for details

---

**Last Updated**: February 10, 2026  
**Backend Status**: ✅ Running on http://localhost:8000  
**Frontend Status**: ✅ Running on http://localhost:8501
