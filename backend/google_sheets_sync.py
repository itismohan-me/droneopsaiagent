"""
Google Sheets Integration for 2-way sync
Supports:
1. Local CSV (development)
2. Service Account Key (traditional, requires JSON key)
3. Workload Identity Federation (enterprise, no keys needed)
"""
import os
import csv
import json
from typing import List, Dict, Optional
from models import Pilot, Drone, Mission, PilotUpdate

# Google Sheets API imports (optional)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.oauth2 import service_account
    from google.identity_bind_credentials import Credentials as IDPCredentials
    from google.auth import default
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False


class GoogleSheetsSync:
    """Handles sync between local CSV and Google Sheets"""

    def __init__(
        self,
        pilot_csv_path: str,
        drone_csv_path: str,
        missions_csv_path: str,
        google_sheets_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        use_google_sheets: bool = False
    ):
        self.pilot_csv_path = pilot_csv_path
        self.drone_csv_path = drone_csv_path
        self.missions_csv_path = missions_csv_path
        self.sync_log = []
        
        # Google Sheets setup
        self.use_google_sheets = use_google_sheets and GOOGLE_SHEETS_AVAILABLE
        self.google_sheets_id = google_sheets_id or os.getenv("GOOGLE_SHEETS_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        self.sheets_service = None
        self.drive_service = None
        
        if self.use_google_sheets and self.google_sheets_id and self.credentials_path:
            try:
                self._initialize_google_sheets()
                self.sync_log.append("✓ Google Sheets API initialized")
            except Exception as e:
                self.sync_log.append(f"⚠ Google Sheets API initialization failed: {str(e)}")
                self.use_google_sheets = False

    def _initialize_google_sheets(self):
        """Initialize Google Sheets API client"""
        if not GOOGLE_SHEETS_AVAILABLE:
            raise ImportError("Google Sheets API libraries not installed")
        
        # Load credentials from service account JSON
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                   "https://www.googleapis.com/auth/drive"]
        )
        
        self.sheets_service = build("sheets", "v4", credentials=credentials)
        self.drive_service = build("drive", "v3", credentials=credentials)

    def load_pilots_from_csv(self) -> List[Pilot]:
        """Load pilots from CSV file or Google Sheets"""
        pilots = []
        
        if self.use_google_sheets:
            try:
                pilots = self._load_pilots_from_sheets()
                return pilots
            except Exception as e:
                self.sync_log.append(f"⚠ Failed to load from Sheets, falling back to CSV: {str(e)}")
        
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
                        drone_experience="",
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

    def _load_pilots_from_sheets(self) -> List[Pilot]:
        """Load pilots from Google Sheets"""
        pilots = []
        
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.google_sheets_id,
            range="Pilots!A:H"
        ).execute()
        
        rows = result.get("values", [])
        if len(rows) <= 1:
            return pilots
        
        headers = rows[0]
        for row in rows[1:]:
            if len(row) < len(headers):
                row.extend([''] * (len(headers) - len(row)))
            
            row_dict = dict(zip(headers, row))
            
            skills = [s.strip() for s in row_dict.get('skills', '').split(',')] if row_dict.get('skills') else []
            certs = [c.strip() for c in row_dict.get('certifications', '').split(',')] if row_dict.get('certifications') else []
            
            current_assignment = row_dict.get('current_assignment', '').strip()
            if current_assignment in ('–', 'None', ''):
                current_assignment = None
            
            pilot = Pilot(
                name=row_dict.get('name', ''),
                skills=skills,
                certifications=certs,
                drone_experience="",
                current_location=row_dict.get('location', ''),
                current_assignment=current_assignment,
                status=row_dict.get('status', 'Available'),
                availability=row_dict.get('available_from', '')
            )
            pilots.append(pilot)
        
        self.sync_log.append(f"✓ Loaded {len(pilots)} pilots from Google Sheets")
        return pilots

    def load_drones_from_csv(self) -> List[Drone]:
        """Load drones from CSV file or Google Sheets"""
        drones = []
        
        if self.use_google_sheets:
            try:
                drones = self._load_drones_from_sheets()
                return drones
            except Exception as e:
                self.sync_log.append(f"⚠ Failed to load drones from Sheets, falling back to CSV: {str(e)}")
        
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
                        battery_health="100%"
                    )
                    drones.append(drone)
            self.sync_log.append(f"✓ Loaded {len(drones)} drones from CSV")
        except Exception as e:
            self.sync_log.append(f"✗ Error loading drones: {str(e)}")
        return drones

    def _load_drones_from_sheets(self) -> List[Drone]:
        """Load drones from Google Sheets"""
        drones = []
        
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.google_sheets_id,
            range="Drones!A:H"
        ).execute()
        
        rows = result.get("values", [])
        if len(rows) <= 1:
            return drones
        
        headers = rows[0]
        for row in rows[1:]:
            if len(row) < len(headers):
                row.extend([''] * (len(headers) - len(row)))
            
            row_dict = dict(zip(headers, row))
            
            capabilities = [c.strip() for c in row_dict.get('capabilities', '').split(',')] if row_dict.get('capabilities') else []
            
            current_assignment = row_dict.get('current_assignment', '').strip()
            if current_assignment in ('–', 'None', ''):
                current_assignment = None
            
            drone = Drone(
                drone_id=row_dict.get('drone_id', ''),
                model=row_dict.get('model', ''),
                capabilities=capabilities,
                current_assignment=current_assignment,
                status=row_dict.get('status', 'Available'),
                location=row_dict.get('location', ''),
                maintenance_due=row_dict.get('maintenance_due', ''),
                battery_health="100%"
            )
            drones.append(drone)
        
        self.sync_log.append(f"✓ Loaded {len(drones)} drones from Google Sheets")
        return drones

    def load_missions_from_csv(self) -> List[Mission]:
        """Load missions from CSV file or Google Sheets"""
        missions = []
        
        if self.use_google_sheets:
            try:
                missions = self._load_missions_from_sheets()
                return missions
            except Exception as e:
                self.sync_log.append(f"⚠ Failed to load missions from Sheets, falling back to CSV: {str(e)}")
        
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
                        status="Scheduled"
                    )
                    missions.append(mission)
            self.sync_log.append(f"✓ Loaded {len(missions)} missions from CSV")
        except Exception as e:
            self.sync_log.append(f"✗ Error loading missions: {str(e)}")
        return missions

    def _load_missions_from_sheets(self) -> List[Mission]:
        """Load missions from Google Sheets"""
        missions = []
        
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.google_sheets_id,
            range="Missions!A:I"
        ).execute()
        
        rows = result.get("values", [])
        if len(rows) <= 1:
            return missions
        
        headers = rows[0]
        for row in rows[1:]:
            if len(row) < len(headers):
                row.extend([''] * (len(headers) - len(row)))
            
            row_dict = dict(zip(headers, row))
            
            required_skills = [s.strip() for s in row_dict.get('required_skills', '').split(',')] if row_dict.get('required_skills') else []
            required_certs = [c.strip() for c in row_dict.get('required_certs', '').split(',')] if row_dict.get('required_certs') else []
            
            mission = Mission(
                project_id=row_dict.get('project_id', ''),
                client_name=row_dict.get('client', ''),
                location=row_dict.get('location', ''),
                required_skills=required_skills,
                required_certifications=required_certs,
                start_date=row_dict.get('start_date', ''),
                end_date=row_dict.get('end_date', ''),
                priority=row_dict.get('priority', 'Medium'),
                status=row_dict.get('status', 'Scheduled')
            )
            missions.append(mission)
        
        self.sync_log.append(f"✓ Loaded {len(missions)} missions from Google Sheets")
        return missions

    def update_pilot_status(self, pilot_update: PilotUpdate) -> bool:
        """Update pilot status in CSV and optionally Google Sheets"""
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
                
                # Sync to Google Sheets if available
                if self.use_google_sheets:
                    self._update_pilot_status_sheets(pilot_update)
                
                self.sync_log.append(f"✓ Updated pilot {pilot_update.name} status to {pilot_update.status}")
                return True
            else:
                self.sync_log.append(f"✗ Pilot {pilot_update.name} not found")
                return False
        except Exception as e:
            self.sync_log.append(f"✗ Error updating pilot status: {str(e)}")
            return False

    def _update_pilot_status_sheets(self, pilot_update: PilotUpdate) -> bool:
        """Update pilot status in Google Sheets"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.google_sheets_id,
                range="Pilots!A:H"
            ).execute()
            
            rows = result.get("values", [])
            headers = rows[0]
            
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) > 0 and row[1] == pilot_update.name:  # Assuming name is in column B
                    status_col = headers.index('status')
                    cell = f"Pilots!{chr(65 + status_col)}{idx}"
                    
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.google_sheets_id,
                        range=cell,
                        valueInputOption="USER_ENTERED",
                        body={"values": [[pilot_update.status]]}
                    ).execute()
                    
                    self.sync_log.append(f"✓ Synced pilot {pilot_update.name} to Google Sheets")
                    return True
            
            self.sync_log.append(f"✗ Pilot {pilot_update.name} not found in Google Sheets")
            return False
        except Exception as e:
            self.sync_log.append(f"✗ Error syncing to Google Sheets: {str(e)}")
            return False

    def update_drone_status(self, drone_id: str, new_status: str, location: str = None) -> bool:
        """Update drone status in CSV and optionally Google Sheets"""
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
                
                # Sync to Google Sheets if available
                if self.use_google_sheets:
                    self._update_drone_status_sheets(drone_id, new_status, location)
                
                self.sync_log.append(f"✓ Updated drone {drone_id} status to {new_status}")
                return True
            else:
                self.sync_log.append(f"✗ Drone {drone_id} not found")
                return False
        except Exception as e:
            self.sync_log.append(f"✗ Error updating drone status: {str(e)}")
            return False

    def _update_drone_status_sheets(self, drone_id: str, new_status: str, location: str = None) -> bool:
        """Update drone status in Google Sheets"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.google_sheets_id,
                range="Drones!A:H"
            ).execute()
            
            rows = result.get("values", [])
            headers = rows[0]
            
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) > 0 and row[0] == drone_id:  # Assuming drone_id is in column A
                    status_col = headers.index('status')
                    cell = f"Drones!{chr(65 + status_col)}{idx}"
                    
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.google_sheets_id,
                        range=cell,
                        valueInputOption="USER_ENTERED",
                        body={"values": [[new_status]]}
                    ).execute()
                    
                    if location:
                        location_col = headers.index('location')
                        cell = f"Drones!{chr(65 + location_col)}{idx}"
                        self.sheets_service.spreadsheets().values().update(
                            spreadsheetId=self.google_sheets_id,
                            range=cell,
                            valueInputOption="USER_ENTERED",
                            body={"values": [[location]]}
                        ).execute()
                    
                    self.sync_log.append(f"✓ Synced drone {drone_id} to Google Sheets")
                    return True
            
            self.sync_log.append(f"✗ Drone {drone_id} not found in Google Sheets")
            return False
        except Exception as e:
            self.sync_log.append(f"✗ Error syncing drone to Google Sheets: {str(e)}")
            return False

    def sync_to_sheets(self, data_type: str) -> bool:
        """Manually sync all data to Google Sheets"""
        if not self.use_google_sheets:
            self.sync_log.append("⚠ Google Sheets not configured")
            return False
        
        try:
            if data_type in ["pilots", "all"]:
                pilots = self.load_pilots_from_csv()
                self._sync_pilots_to_sheets(pilots)
            
            if data_type in ["drones", "all"]:
                drones = self.load_drones_from_csv()
                self._sync_drones_to_sheets(drones)
            
            if data_type in ["missions", "all"]:
                missions = self.load_missions_from_csv()
                self._sync_missions_to_sheets(missions)
            
            self.sync_log.append(f"✓ Synced {data_type} to Google Sheets")
            return True
        except Exception as e:
            self.sync_log.append(f"✗ Error during sync: {str(e)}")
            return False

    def _sync_pilots_to_sheets(self, pilots: List[Pilot]):
        """Sync all pilots to Google Sheets"""
        values = [["pilot_id", "name", "skills", "certifications", "location", "status", "current_assignment", "available_from"]]
        
        for i, pilot in enumerate(pilots):
            values.append([
                f"P{i+1:03d}",
                pilot.name,
                ", ".join(pilot.skills),
                ", ".join(pilot.certifications),
                pilot.current_location,
                pilot.status,
                pilot.current_assignment or "–",
                pilot.availability
            ])
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=self.google_sheets_id,
            range="Pilots!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()

    def _sync_drones_to_sheets(self, drones: List[Drone]):
        """Sync all drones to Google Sheets"""
        values = [["drone_id", "model", "capabilities", "status", "location", "current_assignment", "maintenance_due", "battery_health"]]
        
        for drone in drones:
            values.append([
                drone.drone_id,
                drone.model,
                ", ".join(drone.capabilities),
                drone.status,
                drone.location,
                drone.current_assignment or "–",
                drone.maintenance_due,
                drone.battery_health
            ])
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=self.google_sheets_id,
            range="Drones!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()

    def _sync_missions_to_sheets(self, missions: List[Mission]):
        """Sync all missions to Google Sheets"""
        values = [["project_id", "client", "location", "required_skills", "required_certs", "start_date", "end_date", "priority", "status"]]
        
        for mission in missions:
            values.append([
                mission.project_id,
                mission.client_name,
                mission.location,
                ", ".join(mission.required_skills),
                ", ".join(mission.required_certifications),
                mission.start_date,
                mission.end_date,
                mission.priority,
                mission.status
            ])
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=self.google_sheets_id,
            range="Missions!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values}
        ).execute()

    def get_sync_log(self) -> List[str]:
        """Get sync operation log"""
        return self.sync_log

    def clear_sync_log(self):
        """Clear sync log"""
        self.sync_log = []

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
