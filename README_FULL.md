# 🚁 Skylark Drones - Operations Coordinator AI Agent

A conversational AI operations manager that sits on top of structured data (Google Sheets) and performs reasoning + coordination for drone fleet management.

## 📋 Overview

The Drone Operations Coordinator is an intelligent system that automates and streamlines the coordination of:
- **Pilot Roster Management** - Track availability, skills, certifications
- **Drone Inventory** - Manage fleet status, capabilities, location
- **Mission Assignment** - Match pilots and drones to projects
- **Conflict Detection** - Automatically identify scheduling/skills/equipment issues
- **Urgent Reassignments** - Handle emergency crew changes

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│           Streamlit Frontend (app.py)               │
│  • Conversational Interface                         │
│  • Dashboard & Analytics                            │
│  • Forms for CRUD operations                        │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/REST
                   ▼
┌─────────────────────────────────────────────────────┐
│        FastAPI Backend (main.py, :8000)             │
│                                                      │
│  • Roster Management Endpoints                      │
│  • Drone Fleet Endpoints                            │
│  • Assignment & Conflict Detection                  │
│  • Urgent Reassignment Handler                      │
│                                                      │
│  ├─ models.py (Data schemas)                        │
│  ├─ conflict_detection.py (Conflict logic)          │
│  └─ google_sheets_sync.py (CSV/Sheets sync)        │
└──────────────────┬──────────────────────────────────┘
                   │ File I/O
                   ▼
┌─────────────────────────────────────────────────────┐
│        Data Layer (CSV Files)                       │
│                                                      │
│  • pilot_roster.csv (→ Google Sheets)               │
│  • drone_fleet.csv (→ Google Sheets)                │
│  • missions.csv (mission database)                  │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or conda
- Google Sheets account (for production sync)

### Local Development

1. **Clone and Setup**
```bash
cd droneopsaiagent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Start Backend**
```bash
python main.py
# Backend runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

3. **Start Frontend (new terminal)**
```bash
streamlit run app.py
# Frontend runs on http://localhost:8501
```

## 📊 Core Features

### 1. Roster Management
- **Query pilots** by skill, certification, or location
- **View availability** with days-until-available counter
- **Update status** (Available / On Leave / Unavailable)
- **Auto-sync** changes back to Google Sheets

### 2. Drone Inventory
- **Fleet overview** with status and capabilities
- **Query drones** by capability or location
- **Track maintenance** with urgent alerts
- **Update drone status** and location

### 3. Assignment Management
- **Validate assignments** before creation
- **Create assignments** with full conflict checking
- **Track all assignments** with dates and resources
- **Receive smart suggestions** for pilot-drone matching

### 4. Conflict Detection

Automatically detects and reports:
- ❌ **Double-booking** (critical) - Pilot/drone assigned to overlapping projects
- ❌ **Certification mismatch** (critical) - Pilot lacks required certifications
- ⚠️ **Skill mismatch** (warning) - Pilot lacks required skills
- ⚠️ **Location mismatch** (warning) - Pilot/drone not at mission location
- ❌ **Maintenance conflict** (critical) - Drone in maintenance during assignment
- ⚠️ **Capability mismatch** (warning) - Drone lacks required capabilities

### 5. Urgent Reassignments
Handle emergency reassignments by:
1. Finding compatible resources
2. Checking for conflicts
3. Auto-selecting best-fit drone
4. Creating new assignment
5. Returning conflict report

## 🤖 AI Agent Capabilities

The system includes a conversational AI interface that understands commands like:

```
"Who's available for photography in San Francisco?"
→ Queries available pilots with Photography skill in SF location

"Show me all drones with thermal imaging"
→ Lists drones with Thermal Imaging capability

"Are there any conflicts?"
→ System-wide conflict scan
```

## 📁 Project Structure

```
droneopsaiagent/
├── main.py                    # FastAPI backend application
├── app.py                     # Streamlit frontend
├── models.py                  # Pydantic data models
├── conflict_detection.py      # Conflict detection engine
├── google_sheets_sync.py      # CSV/Google Sheets sync logic
│
├── pilot_roster.csv           # Pilot database
├── drone_fleet.csv            # Drone database
├── missions.csv               # Mission/project database
│
├── requirements.txt           # Python dependencies
├── DECISION_LOG.md            # Architecture & design decisions
└── README.md                  # This file
```

## 🔧 API Endpoints Reference

### Pilots
- `GET /api/pilots` - Get all pilots
- `GET /api/pilots/{name}` - Get pilot details
- `POST /api/pilots/availability` - Query by skill/cert/location
- `PUT /api/pilots/{name}/status` - Update pilot status

### Drones
- `GET /api/drones` - Get all drones
- `GET /api/drones/{id}` - Get drone details
- `POST /api/drones/query` - Query by capability/location
- `PUT /api/drones/{id}/status` - Update drone status
- `GET /api/drones/maintenance/alert` - Get maintenance alerts

### Assignments
- `GET /api/assignments` - Get all assignments
- `POST /api/assignments/validate` - Validate before creation
- `POST /api/assignments/create` - Create assignment

### Operations
- `GET /api/conflicts/detect` - Scan for all conflicts
- `POST /api/reassignments/urgent` - Emergency reassignment
- `GET /api/stats` - Fleet statistics
- `GET /api/health` - Health check

## 🌐 Google Sheets Integration

### Current (MVP - CSV-Based)
- Reads from local CSV files
- Writes updates back to CSV
- Can be synced to Google Sheets manually

### Production Setup
1. Create Google Sheets with matching columns
2. Set up service account credentials
3. Enable Google Sheets API
4. Update `google_sheets_sync.py` with sheet IDs
5. Enable 2-way sync daemon

## 🚨 Edge Cases Handled

- ❌ Pilot assigned to overlapping dates → Blocked
- ❌ Pilot lacks certification → Blocked
- ❌ Drone in maintenance → Blocked
- ⚠️ Pilot & drone in different locations → Warned
- ✓ Emergency reassignment → Intelligent suggestion
- ✓ No compatible resources → Graceful error handling

## 📤 Deployment

### Streamlit Cloud (Frontend)
```bash
git push origin main
# Connect repo to Streamlit Cloud for auto-deployment
```

### Railway/Render (Backend)
```bash
# Create Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

## 📝 Documentation

See [DECISION_LOG.md](DECISION_LOG.md) for:
- Architecture decisions and trade-offs
- Edge case handling strategies
- Assumptions and limitations
- Future improvements

---

**Built with ❤️ for Skylark Drones**
