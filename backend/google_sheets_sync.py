"""
Google Sheets Integration for 2-way sync
Note: In production, use oauth2 for authentication
For this demo, use service account credentials
"""
import os
import csv
from typing import List, Dict
from models import Pilot, Drone, Mission, PilotUpdate

class GoogleSheetsSync:
    """Handles sync between local CSV and Google Sheets"""

    def __init__(self, pilot_csv_path: str, drone_csv_path: str, missions_csv_path: str):
        self.pilot_csv_path = pilot_csv_path
        self.drone_csv_path = drone_csv_path
        self.missions_csv_path = missions_csv_path
        self.sync_log = []

    def load_pilots_from_csv(self) -> List[Pilot]:
        """Load pilots from CSV file"""
        pilots = []
        try:
            with open(self.pilot_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse comma-separated skills and certifications
                    skills = [s.strip() for s in row['skills'].split(',')] if row['skills'] else []
                    certs = [c.strip() for c in row['certifications'].split(',')] if row['certifications'] else []
                    
                    # Handle "–" as null value
                    current_assignment = row['current_assignment'].strip()
                    if current_assignment in ('–', 'None', ''):
                        current_assignment = None
                    
                    pilot = Pilot(
                        name=row['name'],
                        skills=skills,
                        certifications=certs,
                        drone_experience="",  # Not in new CSV
                        current_location=row['location'],
                        current_assignment=current_assignment,
                        status=row['status'],
                        availability=row['available_from']
                    )
                    pilots.append(pilot)
            self.sync_log.append(f"✓ Loaded {len(pilots)} pilots from CSV")
        except Exception as e:
            self.sync_log.append(f"✗ Error loading pilots: {str(e)}")
        return pilots

    def load_drones_from_csv(self) -> List[Drone]:
        """Load drones from CSV file"""
        drones = []
        try:
            with open(self.drone_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse comma-separated capabilities
                    capabilities = [c.strip() for c in row['capabilities'].split(',')] if row['capabilities'] else []
                    
                    # Handle "–" as null value
                    current_assignment = row['current_assignment'].strip()
                    if current_assignment in ('–', 'None', ''):
                        current_assignment = None
                    
                    drone = Drone(
                        drone_id=row['drone_id'],
                        model=row['model'],
                        capabilities=capabilities,
                        current_assignment=current_assignment,
                        status=row['status'],
                        location=row['location'],
                        maintenance_due=row['maintenance_due'],
                        battery_health="100%"  # Not in new CSV, defaulting
                    )
                    drones.append(drone)
            self.sync_log.append(f"✓ Loaded {len(drones)} drones from CSV")
        except Exception as e:
            self.sync_log.append(f"✗ Error loading drones: {str(e)}")
        return drones

    def load_missions_from_csv(self) -> List[Mission]:
        """Load missions from CSV file"""
        missions = []
        try:
            with open(self.missions_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse comma-separated skills and certs
                    required_skills = [s.strip() for s in row['required_skills'].split(',')] if row['required_skills'] else []
                    required_certs = [c.strip() for c in row['required_certs'].split(',')] if row['required_certs'] else []
                    
                    mission = Mission(
                        project_id=row['project_id'],
                        client_name=row['client'],
                        location=row['location'],
                        required_skills=required_skills,
                        required_certifications=required_certs,
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        priority=row['priority'],
                        status="Scheduled"  # Default status, not in new CSV
                    )
                    missions.append(mission)
            self.sync_log.append(f"✓ Loaded {len(missions)} missions from CSV")
        except Exception as e:
            self.sync_log.append(f"✗ Error loading missions: {str(e)}")
        return missions

    def update_pilot_status(self, pilot_update: PilotUpdate) -> bool:
        """Update pilot status and sync back to CSV"""
        try:
            pilots_data = []
            updated = False

            with open(self.pilot_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['name'] == pilot_update.name:
                        row['status'] = pilot_update.status
                        updated = True
                    pilots_data.append(row)

            if updated:
                with open(self.pilot_csv_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(pilots_data)
                self.sync_log.append(f"✓ Updated pilot {pilot_update.name} status to {pilot_update.status}")
                return True
            else:
                self.sync_log.append(f"✗ Pilot {pilot_update.name} not found")
                return False
        except Exception as e:
            self.sync_log.append(f"✗ Error updating pilot status: {str(e)}")
            return False

    def update_drone_status(self, drone_id: str, new_status: str, location: str = None) -> bool:
        """Update drone status and sync back to CSV"""
        try:
            drones_data = []
            updated = False

            with open(self.drone_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['drone_id'] == drone_id:
                        row['status'] = new_status
                        if location:
                            row['location'] = location
                        updated = True
                    drones_data.append(row)

            if updated:
                with open(self.drone_csv_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(drones_data)
                self.sync_log.append(f"✓ Updated drone {drone_id} status to {new_status}")
                return True
            else:
                self.sync_log.append(f"✗ Drone {drone_id} not found")
                return False
        except Exception as e:
            self.sync_log.append(f"✗ Error updating drone status: {str(e)}")
            return False

    def get_sync_log(self) -> List[str]:
        """Get sync operation log"""
        return self.sync_log

    def clear_sync_log(self):
        """Clear sync log"""
        self.sync_log = []
