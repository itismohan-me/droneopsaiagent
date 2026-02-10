import os
import json
from google_sheets_sync import GoogleSheetsSync

os.environ['GOOGLE_SHEETS_ID'] = '1H7zd4Pb25Xp_KB72l0ZZVycxpUB2kGXz0sBwNvUearw'
creds_path = os.path.join(os.path.dirname(__file__), 'credentials', 'service_account.json')
print('Using credentials:', creds_path)
try:
    g = GoogleSheetsSync(
        pilot_csv_path=os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot_roster.csv'),
        drone_csv_path=os.path.join(os.path.dirname(__file__), '..', 'data', 'drone_fleet.csv'),
        missions_csv_path=os.path.join(os.path.dirname(__file__), '..', 'data', 'missions.csv'),
        google_sheets_id=os.environ['GOOGLE_SHEETS_ID'],
        credentials_path=creds_path,
        use_google_sheets=True
    )
    print('use_google_sheets:', g.use_google_sheets)
    pilots = g._load_pilots_from_sheets() if g.use_google_sheets else []
    print('Pilots loaded from sheets:', len(pilots))
    print(json.dumps([p.__dict__ for p in pilots], indent=2)[:2000])
except Exception as e:
    print('ERROR', e)
