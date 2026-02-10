import os, traceback
os.environ['GOOGLE_SHEETS_ID']='1H7zd4Pb25Xp_KB72l0ZZVycxpUB2kGXz0sBwNvUearw'
creds_path = os.path.join(os.path.dirname(__file__), 'credentials', 'service_account.json')
print('Using credentials:', creds_path)
from google_sheets_sync import GoogleSheetsSync
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
    try:
        pilots = g._load_pilots_from_sheets() if g.use_google_sheets else []
        print('Pilots loaded from sheets:', len(pilots))
        for p in pilots:
            print('PILOT:', p.__dict__)
    except Exception as e:
        print('Inner error repr:', repr(e))
        traceback.print_exc()
except Exception as e:
    print('Outer error repr:', repr(e))
    traceback.print_exc()
