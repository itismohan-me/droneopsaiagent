from datetime import datetime
from typing import List, Dict
from models import Conflict, ConflictReport, Pilot, Drone, Mission, Assignment

class ConflictDetector:
    """Detects conflicts in pilot-drone-mission assignments"""

    def __init__(self, pilots: List[Pilot], drones: List[Drone], missions: List[Mission]):
        self.pilots = {p.name: p for p in pilots}
        self.drones = {d.drone_id: d for d in drones}
        self.missions = {m.project_id: m for m in missions}
        self.conflicts: List[Conflict] = []

    def check_double_booking(self, pilot_name: str, new_project_id: str, new_start: str, new_end: str) -> List[Conflict]:
        """Detect if pilot is already assigned to overlapping projects"""
        conflicts = []
        pilot = self.pilots.get(pilot_name)
        
        if not pilot or not pilot.current_assignment:
            return conflicts

        current_mission = self.missions.get(pilot.current_assignment)
        if not current_mission:
            return conflicts

        # Check for date overlap
        if self._dates_overlap(current_mission.start_date, current_mission.end_date, new_start, new_end):
            conflicts.append(Conflict(
                type="double_booking",
                severity="critical",
                description=f"Pilot {pilot_name} already assigned to {pilot.current_assignment} during overlapping dates",
                affected_entity=pilot_name,
                suggestion=f"Reassign pilot from {pilot.current_assignment} or choose different pilot"
            ))

        return conflicts

    def check_drone_double_booking(self, drone_id: str, new_project_id: str, new_start: str, new_end: str) -> List[Conflict]:
        """Detect if drone is already assigned to overlapping projects"""
        conflicts = []
        drone = self.drones.get(drone_id)
        
        if not drone or not drone.current_assignment:
            return conflicts

        current_mission = self.missions.get(drone.current_assignment)
        if not current_mission:
            return conflicts

        # Check for date overlap
        if self._dates_overlap(current_mission.start_date, current_mission.end_date, new_start, new_end):
            conflicts.append(Conflict(
                type="double_booking",
                severity="critical",
                description=f"Drone {drone_id} already assigned to {drone.current_assignment} during overlapping dates",
                affected_entity=drone_id,
                suggestion=f"Use a different drone or reassign {drone_id} from {drone.current_assignment}"
            ))

        return conflicts

    def check_skill_mismatch(self, pilot_name: str, project_id: str) -> List[Conflict]:
        """Detect if pilot lacks required skills"""
        conflicts = []
        pilot = self.pilots.get(pilot_name)
        mission = self.missions.get(project_id)

        if not pilot or not mission:
            return conflicts

        missing_skills = [s for s in mission.required_skills if s not in pilot.skills]
        if missing_skills:
            conflicts.append(Conflict(
                type="skill_mismatch",
                severity="warning",
                description=f"Pilot {pilot_name} lacks required skills: {', '.join(missing_skills)}",
                affected_entity=pilot_name,
                suggestion=f"Consider training pilot or selecting different pilot with skills: {', '.join(missing_skills)}"
            ))

        return conflicts

    def check_certification_mismatch(self, pilot_name: str, project_id: str) -> List[Conflict]:
        """Detect if pilot lacks required certifications"""
        conflicts = []
        pilot = self.pilots.get(pilot_name)
        mission = self.missions.get(project_id)

        if not pilot or not mission:
            return conflicts

        missing_certs = [c for c in mission.required_certifications if c not in pilot.certifications]
        if missing_certs:
            conflicts.append(Conflict(
                type="certification_mismatch",
                severity="critical",
                description=f"Pilot {pilot_name} lacks required certifications: {', '.join(missing_certs)}",
                affected_entity=pilot_name,
                suggestion=f"Select pilot with certifications: {', '.join(missing_certs)}"
            ))

        return conflicts

    def check_location_mismatch(self, pilot_name: str, drone_id: str, project_id: str) -> List[Conflict]:
        """Detect if pilot and drone are in different locations from mission"""
        conflicts = []
        pilot = self.pilots.get(pilot_name)
        drone = self.drones.get(drone_id)
        mission = self.missions.get(project_id)

        if not pilot or not drone or not mission:
            return conflicts

        if pilot.current_location != mission.location:
            conflicts.append(Conflict(
                type="location_mismatch",
                severity="warning",
                description=f"Pilot {pilot_name} in {pilot.current_location}, mission in {mission.location}",
                affected_entity=pilot_name,
                suggestion=f"Plan for pilot travel or select pilot in {mission.location}"
            ))

        if drone.location != mission.location:
            conflicts.append(Conflict(
                type="location_mismatch",
                severity="warning",
                description=f"Drone {drone_id} in {drone.location}, mission in {mission.location}",
                affected_entity=drone_id,
                suggestion=f"Plan for drone transport or select drone in {mission.location}"
            ))

        return conflicts

    def check_maintenance_conflict(self, drone_id: str, new_start: str, new_end: str) -> List[Conflict]:
        """Detect if drone maintenance is due during assignment period"""
        conflicts = []
        drone = self.drones.get(drone_id)

        if not drone:
            return conflicts

        if drone.status == "In Maintenance":
            conflicts.append(Conflict(
                type="maintenance_conflict",
                severity="critical",
                description=f"Drone {drone_id} is currently in maintenance",
                affected_entity=drone_id,
                suggestion=f"Wait for maintenance to complete or select different drone"
            ))

        # Check if maintenance is due during assignment
        try:
            maintenance_date = datetime.strptime(drone.maintenance_due, "%Y-%m-%d")
            start_date = datetime.strptime(new_start, "%Y-%m-%d")
            end_date = datetime.strptime(new_end, "%Y-%m-%d")

            if start_date <= maintenance_date <= end_date:
                conflicts.append(Conflict(
                    type="maintenance_conflict",
                    severity="warning",
                    description=f"Drone {drone_id} maintenance due on {drone.maintenance_due}, during assignment",
                    affected_entity=drone_id,
                    suggestion=f"Schedule maintenance before {new_start} or after {new_end}"
                ))
        except ValueError:
            pass

        return conflicts

    def check_drone_capability_match(self, drone_id: str, project_id: str) -> List[Conflict]:
        """Detect if drone lacks required capabilities"""
        conflicts = []
        drone = self.drones.get(drone_id)
        mission = self.missions.get(project_id)

        if not drone or not mission:
            return conflicts

        missing_capabilities = [c for c in mission.required_skills if c not in drone.capabilities]
        if missing_capabilities:
            conflicts.append(Conflict(
                type="skill_mismatch",
                severity="warning",
                description=f"Drone {drone_id} lacks required capabilities: {', '.join(missing_capabilities)}",
                affected_entity=drone_id,
                suggestion=f"Select drone with capabilities: {', '.join(missing_capabilities)}"
            ))

        return conflicts

    def validate_assignment(self, pilot_name: str, drone_id: str, project_id: str, 
                           start_date: str, end_date: str) -> ConflictReport:
        """Run all conflict checks for an assignment"""
        all_conflicts = []

        # Run all checks
        all_conflicts.extend(self.check_double_booking(pilot_name, project_id, start_date, end_date))
        all_conflicts.extend(self.check_drone_double_booking(drone_id, project_id, start_date, end_date))
        all_conflicts.extend(self.check_skill_mismatch(pilot_name, project_id))
        all_conflicts.extend(self.check_certification_mismatch(pilot_name, project_id))
        all_conflicts.extend(self.check_location_mismatch(pilot_name, drone_id, project_id))
        all_conflicts.extend(self.check_maintenance_conflict(drone_id, start_date, end_date))
        all_conflicts.extend(self.check_drone_capability_match(drone_id, project_id))

        # Count conflicts by severity
        critical_count = sum(1 for c in all_conflicts if c.severity == "critical")
        warning_count = sum(1 for c in all_conflicts if c.severity == "warning")

        return ConflictReport(
            conflicts_found=len(all_conflicts),
            conflicts=all_conflicts,
            critical_count=critical_count,
            warning_count=warning_count
        )

    def _dates_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Check if two date ranges overlap"""
        try:
            s1 = datetime.strptime(start1, "%Y-%m-%d")
            e1 = datetime.strptime(end1, "%Y-%m-%d")
            s2 = datetime.strptime(start2, "%Y-%m-%d")
            e2 = datetime.strptime(end2, "%Y-%m-%d")
            return not (e1 < s2 or e2 < s1)
        except ValueError:
            return False
