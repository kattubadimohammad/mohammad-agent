from pathlib import Path
import base64
import random
import time

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")
MAX_RETRIES = 4
BASE_BACKOFF_SECONDS = 1.5


class GmailSetupError(RuntimeError):
    """Actionable local OAuth/dependency setup errors."""


def _decode_part(data: str) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_body(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    body = payload.get("body", {}).get("data")
    if mime == "text/plain" and body:
        return _decode_part(body)
    pieces = []
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            pieces.append(_decode_part(part["body"]["data"]))
        elif part.get("parts"):
            nested = _extract_body(part)
            if nested:
                pieces.append(nested)
    if pieces:
        return "\n".join(pieces)
    return _decode_part(body) if body else ""


def _is_retryable_google_error(exc: Exception) -> bool:
    """Return true only for transient rate-limit/server errors, not permission failures."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return False
    if not isinstance(exc, HttpError):
        return False
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status in (429, 500, 502, 503, 504):
        return True
    content = getattr(exc, "content", b"")
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")
    content = str(content).lower()
    return status == 403 and any(term in content for term in ("ratelimitexceeded", "userratelimitexceeded", "backenderror"))


def _execute_with_backoff(request, *, sleep=time.sleep, retries=MAX_RETRIES):
    """Execute a Google API request with bounded exponential backoff."""
    for attempt in range(retries + 1):
        try:
            return request.execute()
        except Exception as exc:
            if attempt >= retries or not _is_retryable_google_error(exc):
                raise
            delay = BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 0.25)
            sleep(delay)


def fetch_job_emails(max_results: int = 5):
    if not CREDENTIALS_FILE.exists():
        raise GmailSetupError(
            "credentials.json was not found. Create an OAuth client ID for a Desktop app, "
            "download its JSON into this project folder, then retry. Never commit it to Git."
        )
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GmailSetupError("Install dependencies first: pip install -r requirements.txt") from exc

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        try:
            TOKEN_FILE.chmod(0o600)
        except OSError:
            pass

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    query = 'newer_than:90d (job OR hiring OR vacancy OR recruiter OR "career opportunity" OR application)'
    safe_max = max(1, min(int(max_results), 100))
    response = _execute_with_backoff(
        service.users().messages().list(userId="me", q=query, maxResults=safe_max)
    )
    results = []
    for index, msg in enumerate(response.get("messages", [])):
        # A small pause reduces burst pressure; retry logic handles transient quotas.
        if index:
            time.sleep(0.15)
        item = _execute_with_backoff(
            service.users().messages().get(userId="me", id=msg["id"], format="full")
        )
        headers = {h["name"].lower(): h["value"] for h in item.get("payload", {}).get("headers", [])}
        body = _extract_body(item.get("payload", {})) or headers.get("snippet", item.get("snippet", ""))
        results.append({
            "message_id": item.get("id", ""),
            "subject": headers.get("subject", "(no subject)"),
            "sender": headers.get("from", ""),
            "date": headers.get("date", ""),
            "body": body[:20000],
        })
    return results
