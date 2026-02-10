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

# Google Sheets integration libraries (optional)
try:
    import gspread
    from google.auth import default as google_auth_default
    from google.oauth2 import service_account
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Keep fallback for googleapiclient if present (not required when using gspread)
try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials as GAPIServiceAccountCreds
    GOOGLEAPI_AVAILABLE = True
except Exception:
    GOOGLEAPI_AVAILABLE = False

# Convenience flag: any supported Google Sheets client available
GOOGLE_SHEETS_AVAILABLE = GSPREAD_AVAILABLE or GOOGLEAPI_AVAILABLE


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
        self.gspread_client = None
        self.gspread_sheet = None
        
        if self.use_google_sheets and self.google_sheets_id:
            try:
                self._initialize_google_sheets()
                self.sync_log.append("✓ Google Sheets client initialized")
            except Exception as e:
                self.sync_log.append(f"⚠ Google Sheets initialization failed: {str(e)}")
                self.use_google_sheets = False

    def _initialize_google_sheets(self):
        """Initialize Google Sheets API client"""
        # Prefer gspread when available - supports ADC and service account JSON
        if GSPREAD_AVAILABLE:
            # Service account JSON provided
            if self.credentials_path and os.path.exists(self.credentials_path):
                self.gspread_client = gspread.service_account(filename=self.credentials_path)
            else:
                # Try ADC
                creds, _ = google_auth_default(scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ])
                self.gspread_client = gspread.authorize(creds)

            # Open sheet
            self.gspread_sheet = self.gspread_client.open_by_key(self.google_sheets_id)
            return

        # Fallback to googleapiclient if gspread isn't installed
        if GOOGLEAPI_AVAILABLE and self.credentials_path and os.path.exists(self.credentials_path):
            creds = GAPIServiceAccountCreds.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            self.sheets_service = build("sheets", "v4", credentials=creds)
            self.drive_service = build("drive", "v3", credentials=creds)
            return

        raise ImportError("No supported Google Sheets client libraries available (install gspread).")

    def _find_worksheet(self, candidates):
        """Return first worksheet matching any candidate title (case-insensitive, normalized)"""
        if not self.gspread_sheet:
            return None
        def norm(s):
            return s.strip().lower().replace(' ', '_').replace('-', '_')
        titles = {norm(ws.title): ws for ws in self.gspread_sheet.worksheets()}
        for c in candidates:
            key = norm(c)
            if key in titles:
                return titles[key]
        return None

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
        # Use gspread records for simplicity if available
        if self.gspread_sheet:
            ws = self._find_worksheet(['Pilots', 'pilot_roster', 'pilot_roaster', 'Pilots Roster', 'Pilot Roster'])
            if not ws:
                raise Exception('Pilots worksheet not found')
            records = ws.get_all_records()
            for rec in records:
                skills = [s.strip() for s in rec.get('skills', '').split(',')] if rec.get('skills') else []
                certs = [c.strip() for c in rec.get('certifications', '').split(',')] if rec.get('certifications') else []
                current_assignment = (rec.get('current_assignment') or '').strip()
                if current_assignment in ('–', 'None', ''):
                    current_assignment = None
                pilot = Pilot(
                    name=rec.get('name', ''),
                    skills=skills,
                    certifications=certs,
                    drone_experience="",
                    current_location=rec.get('location', ''),
                    current_assignment=current_assignment,
                    status=rec.get('status', 'Available'),
                    availability=rec.get('available_from', '')
                )
                pilots.append(pilot)
            self.sync_log.append(f"✓ Loaded {len(pilots)} pilots from Google Sheets (gspread)")
            return pilots

        # Fallback: use googleapiclient if initialized
        if self.sheets_service:
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
            self.sync_log.append(f"✓ Loaded {len(pilots)} pilots from Google Sheets (gapi)")
            return pilots

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
        
        if self.gspread_sheet:
            ws = self._find_worksheet(['Drones', 'drone_fleet', 'drone fleet', 'Drone Fleet'])
            if not ws:
                raise Exception('Drones worksheet not found')
            records = ws.get_all_records()
            for rec in records:
                capabilities = [c.strip() for c in rec.get('capabilities', '').split(',')] if rec.get('capabilities') else []
                current_assignment = (rec.get('current_assignment') or '').strip()
                if current_assignment in ('–', 'None', ''):
                    current_assignment = None
                drone = Drone(
                    drone_id=rec.get('drone_id', ''),
                    model=rec.get('model', ''),
                    capabilities=capabilities,
                    current_assignment=current_assignment,
                    status=rec.get('status', 'Available'),
                    location=rec.get('location', ''),
                    maintenance_due=rec.get('maintenance_due', ''),
                    battery_health=rec.get('battery_health', '100%')
                )
                drones.append(drone)
            self.sync_log.append(f"✓ Loaded {len(drones)} drones from Google Sheets (gspread)")
            return drones

        if self.sheets_service:
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
                    battery_health=row_dict.get('battery_health', '100%')
                )
                drones.append(drone)
            self.sync_log.append(f"✓ Loaded {len(drones)} drones from Google Sheets (gapi)")
            return drones

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
        
        if self.gspread_sheet:
            ws = self._find_worksheet(['Missions', 'missions'])
            if not ws:
                raise Exception('Missions worksheet not found')
            records = ws.get_all_records()
            for rec in records:
                required_skills = [s.strip() for s in rec.get('required_skills', '').split(',')] if rec.get('required_skills') else []
                required_certs = [c.strip() for c in rec.get('required_certs', '').split(',')] if rec.get('required_certs') else []
                mission = Mission(
                    project_id=rec.get('project_id', ''),
                    client_name=rec.get('client', ''),
                    location=rec.get('location', ''),
                    required_skills=required_skills,
                    required_certifications=required_certs,
                    start_date=rec.get('start_date', ''),
                    end_date=rec.get('end_date', ''),
                    priority=rec.get('priority', 'Medium'),
                    status=rec.get('status', 'Scheduled')
                )
                missions.append(mission)
            self.sync_log.append(f"✓ Loaded {len(missions)} missions from Google Sheets (gspread)")
            return missions

        if self.sheets_service:
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
            self.sync_log.append(f"✓ Loaded {len(missions)} missions from Google Sheets (gapi)")
            return missions

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
            # If using gspread, prefer row/col updates for simplicity
            if self.gspread_sheet:
                ws = self._find_worksheet(['Pilots', 'pilot_roster', 'pilot_roaster', 'Pilots Roster', 'Pilot Roster'])
                if not ws:
                    raise Exception('Pilots worksheet not found')
                headers = ws.row_values(1)
                if 'name' in [h.lower() for h in headers]:
                    # Normalize header case to find status/name indices
                    lower_headers = [h.lower() for h in headers]
                    name_col = lower_headers.index('name') + 1
                    status_col = lower_headers.index('status') + 1
                    # Find matching row
                    values = ws.get_all_values()
                    for idx, row in enumerate(values[1:], start=2):
                        cell_name = row[name_col-1] if len(row) >= name_col else ''
                        if cell_name == pilot_update.name:
                            ws.update_cell(idx, status_col, pilot_update.status)
                            self.sync_log.append(f"✓ Synced pilot {pilot_update.name} to Google Sheets (gspread)")
                            return True
                # Fallback: search via records
                records = ws.get_all_records()
                for i, rec in enumerate(records, start=2):
                    if rec.get('name') == pilot_update.name:
                        headers = ws.row_values(1)
                        status_col = [h.lower() for h in headers].index('status') + 1
                        ws.update_cell(i, status_col, pilot_update.status)
                        self.sync_log.append(f"✓ Synced pilot {pilot_update.name} to Google Sheets (gspread)")
                        return True

            # Fallback to googleapiclient
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.google_sheets_id,
                range="Pilots!A:H"
            ).execute()
            rows = result.get("values", [])
            if not rows:
                self.sync_log.append(f"✗ Pilot {pilot_update.name} not found in Google Sheets")
                return False
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
                    self.sync_log.append(f"✓ Synced pilot {pilot_update.name} to Google Sheets (gapi)")
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
            # Use gspread if available
            if self.gspread_sheet:
                ws = self._find_worksheet(['Drones', 'drone_fleet', 'drone fleet', 'Drone Fleet'])
                if not ws:
                    raise Exception('Drones worksheet not found')
                headers = ws.row_values(1)
                lower_headers = [h.lower() for h in headers]
                try:
                    id_col = lower_headers.index('drone_id') + 1
                    status_col = lower_headers.index('status') + 1
                    location_col = lower_headers.index('location') + 1 if 'location' in lower_headers else None
                except ValueError:
                    id_col = 1
                    status_col = 4
                    location_col = 5

                values = ws.get_all_values()
                for idx, row in enumerate(values[1:], start=2):
                    cell_id = row[id_col-1] if len(row) >= id_col else ''
                    if cell_id == drone_id:
                        ws.update_cell(idx, status_col, new_status)
                        if location and location_col:
                            ws.update_cell(idx, location_col, location)
                        self.sync_log.append(f"✓ Synced drone {drone_id} to Google Sheets (gspread)")
                        return True

            # Fallback to googleapiclient
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.google_sheets_id,
                range="Drones!A:H"
            ).execute()
            rows = result.get("values", [])
            if not rows:
                self.sync_log.append(f"✗ Drone {drone_id} not found in Google Sheets")
                return False
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
                    
                    self.sync_log.append(f"✓ Synced drone {drone_id} to Google Sheets (gapi)")
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
        
        # Prefer gspread when available
        if self.gspread_sheet:
            ws = self._find_worksheet(['Pilots', 'pilot_roster', 'pilot_roaster', 'Pilots Roster', 'Pilot Roster'])
            if not ws:
                ws = self.gspread_sheet.add_worksheet('Pilots', rows=len(values)+10, cols=10)
            ws.clear()
            ws.update('A1', values)
            return

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
        
        if self.gspread_sheet:
            ws = self._find_worksheet(['Drones', 'drone_fleet', 'drone fleet', 'Drone Fleet'])
            if not ws:
                ws = self.gspread_sheet.add_worksheet('Drones', rows=len(values)+10, cols=10)
            ws.clear()
            ws.update('A1', values)
            return

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
        
        if self.gspread_sheet:
            ws = self._find_worksheet(['Missions', 'missions'])
            if not ws:
                ws = self.gspread_sheet.add_worksheet('Missions', rows=len(values)+10, cols=10)
            ws.clear()
            ws.update('A1', values)
            return

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
                # Sync to Google Sheets if available
                if self.use_google_sheets:
                    try:
                        self._update_pilot_status_sheets(pilot_update)
                    except Exception as e:
                        self.sync_log.append(f"⚠ Sheet sync failed: {str(e)}")

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
