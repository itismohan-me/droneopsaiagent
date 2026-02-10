from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Pilot Models
class Pilot(BaseModel):
    name: str
    skills: List[str]
    certifications: List[str]
    drone_experience: str
    current_location: str
    current_assignment: Optional[str]
    status: str  # Available, On Leave, Unavailable
    availability: str

class PilotUpdate(BaseModel):
    name: str
    status: str  # Available, On Leave, Unavailable

# Drone Models
class Drone(BaseModel):
    drone_id: str
    model: str
    capabilities: List[str]
    current_assignment: Optional[str]
    status: str  # Available, Deployed, In Maintenance
    location: str
    maintenance_due: str
    battery_health: str

class DroneStatusUpdate(BaseModel):
    drone_id: str
    status: str
    location: Optional[str] = None

# Mission Models
class Mission(BaseModel):
    project_id: str
    client_name: str
    location: str
    required_skills: List[str]
    required_certifications: List[str]
    start_date: str
    end_date: str
    priority: str  # Critical, High, Medium, Low
    status: str  # In Progress, Scheduled, Completed

# Assignment Models
class Assignment(BaseModel):
    pilot_name: str
    drone_id: str
    project_id: str
    start_date: str
    end_date: str

class AssignmentResponse(BaseModel):
    success: bool
    message: str
    assignment: Optional[Assignment] = None
    warnings: List[str] = []

# Conflict Detection Models
class Conflict(BaseModel):
    type: str  # "double_booking", "skill_mismatch", "location_mismatch", "certification_mismatch", "maintenance_conflict"
    severity: str  # "critical", "warning"
    description: str
    affected_entity: str
    suggestion: Optional[str] = None

class ConflictReport(BaseModel):
    conflicts_found: int
    conflicts: List[Conflict]
    critical_count: int
    warning_count: int

# Query Response Models
class PilotAvailabilityQuery(BaseModel):
    skill: Optional[str] = None
    certification: Optional[str] = None
    location: Optional[str] = None

class PilotAvailabilityResponse(BaseModel):
    matching_pilots: List[Pilot]
    count: int

class FleetQuery(BaseModel):
    capability: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None

class FleetResponse(BaseModel):
    matching_drones: List[Drone]
    count: int

# Reassignment Models
class ReassignmentRequest(BaseModel):
    pilot_name: str
    new_project_id: str
    reason: str  # "emergency", "conflict_resolution", "performance", "availability"

class ReassignmentResponse(BaseModel):
    success: bool
    message: str
    old_assignment: Optional[str] = None
    new_assignment: Optional[str] = None
    conflicts_resolved: Optional[List[Conflict]] = None
