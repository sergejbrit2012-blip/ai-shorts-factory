"""Run locally once to authorize your own YouTube channel and create token.json."""
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
SCOPES=['https://www.googleapis.com/auth/youtube.upload']
secret=Path('client_secret.json')
if not secret.exists():
    raise SystemExit('Put your OAuth Desktop client JSON here as client_secret.json')
flow=InstalledAppFlow.from_client_secrets_file(str(secret),SCOPES)
creds=flow.run_local_server(port=0,access_type='offline',prompt='consent')
Path('token.json').write_text(creds.to_json(),encoding='utf-8')
print('Created token.json. Keep it secret; never commit it to Git.')
