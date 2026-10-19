from pathlib import Path
import base64
SCOPES=['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE=Path('credentials.json'); TOKEN_FILE=Path('token.json')
class GmailSetupError(RuntimeError): pass
def _decode_part(data: str) -> str:
    if not data: return ''
    try: return base64.urlsafe_b64decode(data+'='*(-len(data)%4)).decode('utf-8',errors='replace')
    except Exception: return ''
def _extract_body(payload: dict) -> str:
    mime=payload.get('mimeType',''); body=payload.get('body',{}).get('data')
    if mime=='text/plain' and body: return _decode_part(body)
    pieces=[]
    for part in payload.get('parts',[]) or []:
        if part.get('mimeType')=='text/plain' and part.get('body',{}).get('data'): pieces.append(_decode_part(part['body']['data']))
        elif part.get('parts'): pieces.append(_extract_body(part))
    if pieces: return '\\n'.join(pieces)
    return _decode_part(body) if body else ''
def fetch_job_emails(max_results: int=30):
    if not CREDENTIALS_FILE.exists(): raise GmailSetupError('credentials.json was not found. Create OAuth credentials in Google Cloud Console (OAuth client ID → Desktop app), download the JSON into this project folder, then retry.')
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e: raise GmailSetupError('Install dependencies first: pip install -r requirements.txt') from e
    creds=None
    if TOKEN_FILE.exists(): creds=Credentials.from_authorized_user_file(str(TOKEN_FILE),SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            flow=InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE),SCOPES); creds=flow.run_local_server(port=0,access_type='offline',prompt='consent')
        TOKEN_FILE.write_text(creds.to_json(),encoding='utf-8')
        try: TOKEN_FILE.chmod(0o600)
        except OSError: pass
    service=build('gmail','v1',credentials=creds,cache_discovery=False)
    query='newer_than:90d (job OR hiring OR vacancy OR recruiter OR "career opportunity" OR application)'
    response=service.users().messages().list(userId='me',q=query,maxResults=max_results).execute(); results=[]
    for msg in response.get('messages',[]):
        item=service.users().messages().get(userId='me',id=msg['id'],format='full').execute()
        headers={h['name'].lower():h['value'] for h in item.get('payload',{}).get('headers',[])}; body=_extract_body(item.get('payload',{})) or headers.get('snippet',item.get('snippet',''))
        results.append({'message_id':item.get('id',''),'subject':headers.get('subject','(no subject)'),'sender':headers.get('from',''),'date':headers.get('date',''),'body':body[:20000]})
    return results
