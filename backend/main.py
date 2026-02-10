"""
FastAPI Backend for Drone Operations AI Agent
Handles all core logic and provides endpoints for the Streamlit frontend
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import List, Optional
import math
from datetime import datetime

from models import (
    Pilot, Drone, Mission, Assignment, AssignmentResponse,
    PilotUpdate, DroneStatusUpdate, ConflictReport,
    PilotAvailabilityQuery, PilotAvailabilityResponse,
    FleetQuery, FleetResponse, ReassignmentRequest, ReassignmentResponse
)
from conflict_detection import ConflictDetector
from google_sheets_sync import GoogleSheetsSync

# Initialize FastAPI app
app = FastAPI(title="Drone Operations Coordinator", version="1.0.0")

# Add CORS middleware for Streamlit integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data sync
csv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
use_google_sheets = os.getenv("USE_GOOGLE_SHEETS", "false").lower() == "true"
sync = GoogleSheetsSync(
    pilot_csv_path=os.path.join(csv_dir, "pilot_roster.csv"),
    drone_csv_path=os.path.join(csv_dir, "drone_fleet.csv"),
    missions_csv_path=os.path.join(csv_dir, "missions.csv"),
    google_sheets_id=os.getenv("GOOGLE_SHEETS_ID"),
    credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH"),
    use_google_sheets=use_google_sheets
)

# Load initial data
pilots = sync.load_pilots_from_csv()
drones = sync.load_drones_from_csv()
missions = sync.load_missions_from_csv()

# Initialize conflict detector
conflict_detector = ConflictDetector(pilots, drones, missions)

# In-memory assignment tracking
assignments = []

# ============================================================================
# ROSTER MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/pilots")
async def get_all_pilots() -> List[Pilot]:
    """Get all pilots"""
    return pilots

@app.post("/api/pilots/availability")
async def query_pilot_availability(query: PilotAvailabilityQuery) -> PilotAvailabilityResponse:
    """Query pilots by skill, certification, or location"""
    matching = []

    for pilot in pilots:
        matches = True

        if query.skill and query.skill not in pilot.skills:
            matches = False
        if query.certification and query.certification not in pilot.certifications:
            matches = False
        if query.location and pilot.current_location != query.location:
            matches = False

        if matches and pilot.status == "Available":
            matching.append(pilot)

    return PilotAvailabilityResponse(matching_pilots=matching, count=len(matching))

@app.put("/api/pilots/{pilot_name}/status")
async def update_pilot_status(pilot_name: str, update: PilotUpdate) -> dict:
    """Update pilot status (Available/On Leave/Unavailable) and sync to CSV"""
    global pilots
    
    # Find and update pilot
    pilot_found = False
    for pilot in pilots:
        if pilot.name == pilot_name:
            pilot.status = update.status
            pilot_found = True
            break

    if not pilot_found:
        raise HTTPException(status_code=404, detail=f"Pilot {pilot_name} not found")

    # Sync to CSV
    sync.clear_sync_log()
    success = sync.update_pilot_status(update)

    return {
        "success": success,
        "message": f"Updated {pilot_name} status to {update.status}",
        "sync_log": sync.get_sync_log()
    }

@app.get("/api/pilots/{pilot_name}")
async def get_pilot_details(pilot_name: str) -> dict:
    """Get detailed information about a specific pilot"""
    for pilot in pilots:
        if pilot.name == pilot_name:
            return {
                "pilot": pilot,
                "assignment": pilot.current_assignment,
                "days_until_available": _calculate_days_until_available(pilot.availability)
            }
    raise HTTPException(status_code=404, detail=f"Pilot {pilot_name} not found")

# ============================================================================
# DRONE INVENTORY ENDPOINTS
# ============================================================================

@app.get("/api/drones")
async def get_all_drones() -> List[Drone]:
    """Get all drones in fleet"""
    return drones

@app.post("/api/drones/query")
async def query_fleet(query: FleetQuery) -> FleetResponse:
    """Query drones by capability, availability, or location"""
    matching = []

    for drone in drones:
        matches = True

        if query.capability and query.capability not in drone.capabilities:
            matches = False
        if query.location and drone.location != query.location:
            matches = False
        if query.status and drone.status != query.status:
            matches = False

        if matches and drone.status == "Available":
            matching.append(drone)

    return FleetResponse(matching_drones=matching, count=len(matching))

@app.put("/api/drones/{drone_id}/status")
async def update_drone_status(drone_id: str, update: DroneStatusUpdate) -> dict:
    """Update drone status and sync to CSV"""
    global drones
    
    # Find and update drone
    drone_found = False
    for drone in drones:
        if drone.drone_id == drone_id:
            drone.status = update.status
            if update.location:
                drone.location = update.location
            drone_found = True
            break

    if not drone_found:
        raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")

    # Sync to CSV
    sync.clear_sync_log()
    success = sync.update_drone_status(drone_id, update.status, update.location)

    return {
        "success": success,
        "message": f"Updated {drone_id} status to {update.status}",
        "sync_log": sync.get_sync_log()
    }

@app.get("/api/drones/{drone_id}")
async def get_drone_details(drone_id: str) -> dict:
    """Get detailed information about a specific drone"""
    for drone in drones:
        if drone.drone_id == drone_id:
            return {
                "drone": drone,
                "assignment": drone.current_assignment,
                "maintenance_urgent": _is_maintenance_urgent(drone.maintenance_due)
            }
    raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found")

@app.get("/api/drones/maintenance/alert")
async def get_maintenance_alerts() -> dict:
    """Get drones requiring attention for maintenance"""
    alerts = []
    for drone in drones:
        if drone.status == "In Maintenance":
            alerts.append({
                "drone_id": drone.drone_id,
                "issue": "Currently in maintenance",
                "severity": "high"
            })
        elif _is_maintenance_urgent(drone.maintenance_due):
            alerts.append({
                "drone_id": drone.drone_id,
                "issue": f"Maintenance due on {drone.maintenance_due}",
                "severity": "medium"
            })

    return {"maintenance_alerts": alerts, "count": len(alerts)}

# ============================================================================
# INTERNAL VALIDATION HELPER
# ============================================================================

def _validate_assignment_internal(pilot_name: str, drone_id: str, project_id: str,
                                   start_date: str, end_date: str) -> ConflictReport:
    """Internal validation logic used by both endpoints"""
    global conflict_detector
    
    # Reload conflict detector with latest data
    conflict_detector = ConflictDetector(pilots, drones, missions)
    
    report = conflict_detector.validate_assignment(
        pilot_name,
        drone_id,
        project_id,
        start_date,
        end_date
    )
    return report

# ============================================================================
# MISSION & ASSIGNMENT ENDPOINTS
# ============================================================================

@app.get("/api/missions")
async def get_all_missions() -> List[Mission]:
    """Get all missions"""
    return missions

@app.get("/api/assignments")
async def get_all_assignments() -> List[dict]:
    """Get all active assignments"""
    return assignments

@app.post("/api/assignments/validate")
async def validate_assignment(assignment: Assignment) -> ConflictReport:
    """Validate an assignment and return conflict report"""
    return _validate_assignment_internal(
        assignment.pilot_name,
        assignment.drone_id,
        assignment.project_id,
        assignment.start_date,
        assignment.end_date
    )

@app.post("/api/assignments/create")
async def create_assignment(assignment: Assignment) -> AssignmentResponse:
    """Create a new assignment with validation"""
    global pilots, drones, assignments
    
    # Validate assignment using internal logic
    report = _validate_assignment_internal(
        assignment.pilot_name,
        assignment.drone_id,
        assignment.project_id,
        assignment.start_date,
        assignment.end_date
    )

    if report.critical_count > 0:
        return AssignmentResponse(
            success=False,
            message=f"Cannot create assignment: {report.critical_count} critical conflicts",
            warnings=[c.description for c in report.conflicts if c.severity == "critical"]
        )

    # Create assignment
    assignments.append({
        "pilot_name": assignment.pilot_name,
        "drone_id": assignment.drone_id,
        "project_id": assignment.project_id,
        "start_date": assignment.start_date,
        "end_date": assignment.end_date,
        "created_at": datetime.now().isoformat()
    })

    # Update pilot and drone assignments
    for pilot in pilots:
        if pilot.name == assignment.pilot_name:
            pilot.current_assignment = assignment.project_id
            break

    for drone in drones:
        if drone.drone_id == assignment.drone_id:
            drone.current_assignment = assignment.project_id
            drone.status = "Deployed"
            break

    return AssignmentResponse(
        success=True,
        message=f"Assignment created successfully",
        assignment=assignment,
        warnings=[c.description for c in report.conflicts if c.severity == "warning"]
    )

# ============================================================================
# CONFLICT DETECTION ENDPOINTS
# ============================================================================

@app.get("/api/conflicts/detect")
async def detect_all_conflicts() -> dict:
    """Scan entire system for conflicts"""
    all_conflicts = []

    for pilot in pilots:
        if pilot.current_assignment:
            # Check all pilot conflicts
            report = await validate_assignment(Assignment(
                pilot_name=pilot.name,
                drone_id="SCAN",
                project_id=pilot.current_assignment,
                start_date="2026-02-01",
                end_date="2026-12-31"
            ))
            all_conflicts.extend(report.conflicts)

    # Remove duplicates
    unique_conflicts = []
    seen = set()
    for conflict in all_conflicts:
        key = (conflict.type, conflict.affected_entity)
        if key not in seen:
            unique_conflicts.append(conflict)
            seen.add(key)

    return {
        "total_conflicts": len(unique_conflicts),
        "conflicts": unique_conflicts
    }

# ============================================================================
# URGENT REASSIGNMENT ENDPOINTS
# ============================================================================

@app.post("/api/reassignments/urgent")
async def handle_urgent_reassignment(request: ReassignmentRequest) -> ReassignmentResponse:
    """Handle urgent pilot reassignment with conflict resolution"""
    global pilots, assignments

    # Find pilot
    pilot_found = False
    old_assignment = None
    for pilot in pilots:
        if pilot.name == request.pilot_name:
            old_assignment = pilot.current_assignment
            pilot_found = True
            break

    if not pilot_found:
        return ReassignmentResponse(
            success=False,
            message=f"Pilot {request.pilot_name} not found"
        )

    # Find target mission
    target_mission = None
    for mission in missions:
        if mission.project_id == request.new_project_id:
            target_mission = mission
            break

    if not target_mission:
        return ReassignmentResponse(
            success=False,
            message=f"Project {request.new_project_id} not found"
        )

    # Find available drones with required capabilities
    compatible_drones = []
    for drone in drones:
        if drone.status == "Available":
            # Check if drone has all required skills/capabilities
            has_all_capabilities = all(
                cap in drone.capabilities 
                for cap in target_mission.required_skills
            )
            if has_all_capabilities:
                compatible_drones.append(drone)

    if not compatible_drones:
        return ReassignmentResponse(
            success=False,
            message=f"No compatible drones available for {request.new_project_id}"
        )

    # Create new assignment with first available drone
    selected_drone = compatible_drones[0]
    new_assignment = Assignment(
        pilot_name=request.pilot_name,
        drone_id=selected_drone.drone_id,
        project_id=request.new_project_id,
        start_date=target_mission.start_date,
        end_date=target_mission.end_date
    )

    # Validate new assignment
    validation_report = _validate_assignment_internal(
        request.pilot_name,
        selected_drone.drone_id,
        request.new_project_id,
        target_mission.start_date,
        target_mission.end_date
    )
    
    # If critical conflicts, reject
    if validation_report.critical_count > 0:
        return ReassignmentResponse(
            success=False,
            message=f"Cannot reassign: {validation_report.critical_count} critical conflict(s)",
            conflicts_resolved=validation_report.conflicts
        )

    # Update pilot and drone assignments
    for pilot in pilots:
        if pilot.name == request.pilot_name:
            pilot.current_assignment = request.new_project_id
            break

    for drone in drones:
        if drone.drone_id == selected_drone.drone_id:
            drone.current_assignment = request.new_project_id
            drone.status = "Deployed"
            break

    # Add to assignments list
    assignments.append({
        "pilot_name": request.pilot_name,
        "drone_id": selected_drone.drone_id,
        "project_id": request.new_project_id,
        "start_date": target_mission.start_date,
        "end_date": target_mission.end_date,
        "reason": request.reason,
        "created_at": datetime.now().isoformat()
    })

    return ReassignmentResponse(
        success=True,
        message=f"Urgent assignment/reassignment successful",
        old_assignment=old_assignment,
        new_assignment=request.new_project_id,
        conflicts_resolved=validation_report.conflicts
    )

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "pilots_count": len(pilots),
        "drones_count": len(drones),
        "missions_count": len(missions),
        "assignments_count": len(assignments)
    }

@app.get("/api/stats")
async def get_statistics() -> dict:
    """Get system statistics"""
    available_pilots = sum(1 for p in pilots if p.status == "Available")
    available_drones = sum(1 for d in drones if d.status == "Available")
    on_leave_pilots = sum(1 for p in pilots if p.status == "On Leave")
    in_maintenance_drones = sum(1 for d in drones if d.status == "In Maintenance")

    return {
        "pilots": {
            "total": len(pilots),
            "available": available_pilots,
            "on_leave": on_leave_pilots,
            "unavailable": len(pilots) - available_pilots - on_leave_pilots
        },
        "drones": {
            "total": len(drones),
            "available": available_drones,
            "deployed": sum(1 for d in drones if d.status == "Deployed"),
            "in_maintenance": in_maintenance_drones
        },
        "missions": {
            "total": len(missions),
            "in_progress": sum(1 for m in missions if m.status == "In Progress"),
            "scheduled": sum(1 for m in missions if m.status == "Scheduled")
        }
    }

# ============================================================================
# GOOGLE SHEETS INTEGRATION
# ============================================================================

@app.get("/api/sync/status")
async def get_sync_status() -> dict:
    """Get sync status and log"""
    return {
        "google_sheets_enabled": sync.use_google_sheets,
        "google_sheets_id": sync.google_sheets_id if sync.use_google_sheets else None,
        "sync_log": sync.get_sync_log(),
        "last_sync": sync.sync_log[-1] if sync.sync_log else None
    }

@app.post("/api/sync/pilots")
async def sync_pilots_to_sheets() -> dict:
    """Manually sync all pilots to Google Sheets"""
    if not sync.use_google_sheets:
        raise HTTPException(
            status_code=400,
            detail="Google Sheets integration not configured. Set USE_GOOGLE_SHEETS=true and provide credentials."
        )
    
    success = sync.sync_to_sheets("pilots")
    return {
        "success": success,
        "message": "Pilots synced to Google Sheets" if success else "Failed to sync pilots",
        "sync_log": sync.get_sync_log()
    }

@app.post("/api/sync/drones")
async def sync_drones_to_sheets() -> dict:
    """Manually sync all drones to Google Sheets"""
    if not sync.use_google_sheets:
        raise HTTPException(
            status_code=400,
            detail="Google Sheets integration not configured. Set USE_GOOGLE_SHEETS=true and provide credentials."
        )
    
    success = sync.sync_to_sheets("drones")
    return {
        "success": success,
        "message": "Drones synced to Google Sheets" if success else "Failed to sync drones",
        "sync_log": sync.get_sync_log()
    }

@app.post("/api/sync/missions")
async def sync_missions_to_sheets() -> dict:
    """Manually sync all missions to Google Sheets"""
    if not sync.use_google_sheets:
        raise HTTPException(
            status_code=400,
            detail="Google Sheets integration not configured. Set USE_GOOGLE_SHEETS=true and provide credentials."
        )
    
    success = sync.sync_to_sheets("missions")
    return {
        "success": success,
        "message": "Missions synced to Google Sheets" if success else "Failed to sync missions",
        "sync_log": sync.get_sync_log()
    }

@app.post("/api/sync/all")
async def sync_all_to_sheets() -> dict:
    """Manually sync all data to Google Sheets"""
    if not sync.use_google_sheets:
        raise HTTPException(
            status_code=400,
            detail="Google Sheets integration not configured. Set USE_GOOGLE_SHEETS=true and provide credentials."
        )
    
    success = sync.sync_to_sheets("all")
    return {
        "success": success,
        "message": "All data synced to Google Sheets" if success else "Failed to sync data",
        "sync_log": sync.get_sync_log()
    }

@app.post("/api/sync/reload")
async def reload_from_sheets() -> dict:
    """Reload all data from Google Sheets or CSV"""
    global pilots, drones, missions, conflict_detector, assignments
    
    try:
        pilots = sync.load_pilots_from_csv()
        drones = sync.load_drones_from_csv()
        missions = sync.load_missions_from_csv()
        conflict_detector = ConflictDetector(pilots, drones, missions)
        assignments = []
        
        return {
            "success": True,
            "message": "Data reloaded successfully",
            "pilots_count": len(pilots),
            "drones_count": len(drones),
            "missions_count": len(missions),
            "sync_log": sync.get_sync_log()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading data: {str(e)}"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _calculate_days_until_available(availability_date: str) -> int:
    """Calculate days until pilot is available"""
    try:
        avail = datetime.strptime(availability_date, "%Y-%m-%d")
        today = datetime.now()
        return (avail - today).days
    except:
        return -1

def _is_maintenance_urgent(maintenance_date: str) -> bool:
    """Check if maintenance is due within 7 days"""
    try:
        maint = datetime.strptime(maintenance_date, "%Y-%m-%d")
        today = datetime.now()
        days_until = (maint - today).days
        return 0 <= days_until <= 7
    except:
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
