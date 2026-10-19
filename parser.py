import re

ROLE_PATTERNS = [
 (r'\\b(data engineer|analytics engineer|etl engineer)\\b','Data Engineer'),
 (r'\\b(data scientist|applied scientist)\\b','Data Scientist'),
 (r'\\b(ai.?/?ml engineer|machine learning engineer|ml engineer)\\b','AI/ML Engineer'),
 (r'\\b(generative ai|genai|agentic ai|llm engineer|ai automation engineer)\\b','Applied AI / GenAI'),
 (r'\\b(data analyst|reporting analyst|analytics analyst)\\b','Data Analyst'),
 (r'\\b(business analyst|mis analyst|mis executive)\\b','Business Analyst / MIS'),
]
def _clean(s: str) -> str: return re.sub(r'\\s+',' ',s or '').strip()
def parse_job_email(subject: str, sender: str, date: str, body: str, message_id: str='') -> dict:
    text=f'{subject}\\n{body}'; title='Unknown role'
    for pattern, normalized in ROLE_PATTERNS:
        if re.search(pattern,text,re.I): title=_clean(subject)[:140] if subject and len(subject.strip())>3 else normalized; break
    company='Unknown company'
    for pattern in [r'(?:company|employer|organization)\\s*[:\\-]\\s*([^\\n|,;]{2,80})',r'(?:at|with)\\s+([A-Z][A-Za-z0-9&.\' -]{1,60})(?:\\s+(?:is hiring|is looking|for the role)|[.,\\n])']:
        m=re.search(pattern,text,re.I)
        if m:
            candidate=_clean(m.group(1)).strip(' .-')
            if candidate and candidate.lower() not in {'the role','our team'}: company=candidate; break
    url_match=re.search(r'https?://[^\\s<>\"\')\\]]+',body or '',re.I)
    url=url_match.group(0).rstrip('.,;') if url_match else ''
    return {'title':title,'company':company,'location':'','application_url':url,'description':_clean(body)[:12000],'source':'Email','email_message_id':message_id,'raw_email':text[:20000],'email_sender':sender,'email_date':date}
