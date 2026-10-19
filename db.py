import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = '''
CREATE TABLE IF NOT EXISTS jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, dedupe_key TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL, company TEXT NOT NULL DEFAULT 'Unknown company', location TEXT DEFAULT '',
 application_url TEXT DEFAULT '', description TEXT DEFAULT '', source TEXT DEFAULT '', email_message_id TEXT,
 raw_email TEXT DEFAULT '', match_score INTEGER DEFAULT 0, matched_skills TEXT DEFAULT '', missing_skills TEXT DEFAULT '',
 status TEXT NOT NULL DEFAULT 'New', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, details TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
'''
def connect(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row; return conn

def init_db(db_path: str):
    with connect(db_path) as conn: conn.executescript(SCHEMA)

def _dedupe_key(item: dict[str, Any]) -> str:
    import hashlib, re
    title = re.sub(r'\\s+', ' ', (item.get('title') or '').strip().lower())
    company = re.sub(r'\\s+', ' ', (item.get('company') or '').strip().lower())
    url = (item.get('application_url') or '').strip().lower().split('?')[0]
    basis = f'url:{url}' if url else f'{title}|{company}'
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()

def upsert_job(db_path: str, item: dict[str, Any]) -> bool:
    key = _dedupe_key(item)
    fields = ['title','company','location','application_url','description','source','email_message_id','raw_email','match_score','matched_skills','missing_skills']
    values = [item.get(k) for k in fields]
    with connect(db_path) as conn:
        cur = conn.execute('''INSERT OR IGNORE INTO jobs (dedupe_key,title,company,location,application_url,description,source,email_message_id,raw_email,match_score,matched_skills,missing_skills) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', [key]+values)
        if cur.rowcount == 1: return True
        conn.execute('''UPDATE jobs SET description=CASE WHEN ?<>'' THEN ? ELSE description END, raw_email=CASE WHEN ?<>'' THEN ? ELSE raw_email END, application_url=CASE WHEN ?<>'' THEN ? ELSE application_url END, match_score=?, matched_skills=?, missing_skills=?, updated_at=CURRENT_TIMESTAMP WHERE dedupe_key=?''', [item.get('description') or '',item.get('description') or '',item.get('raw_email') or '',item.get('raw_email') or '',item.get('application_url') or '',item.get('application_url') or '',item.get('match_score') or 0,item.get('matched_skills') or '',item.get('missing_skills') or '',key])
        return False

def list_jobs(db_path: str):
    with connect(db_path) as conn: return [dict(r) for r in conn.execute('SELECT * FROM jobs ORDER BY created_at DESC, id DESC')]

def update_job_status(db_path: str, job_id: int, status: str):
    if status not in {'New','Review','Approved','Applied','Hold','Rejected'}: raise ValueError('Invalid status')
    with connect(db_path) as conn: conn.execute('UPDATE jobs SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,job_id))

def add_audit(db_path: str, action: str, details: str = ''):
    with connect(db_path) as conn: conn.execute('INSERT INTO audit_log(action,details) VALUES (?,?)',(action,details))
