import re
from urllib.parse import urlparse

# Keep these labels aligned with the role filters in app.py.
ROLE_PATTERNS = [
    (r"\b(data engineer|analytics engineer|etl engineer)\b", "Data Engineer"),
    (r"\b(data scientist|applied scientist)\b", "Data Scientist"),
    (r"\b(ai\s*/?\s*ml engineer|machine learning engineer|ml engineer)\b", "AI/ML Engineer"),
    (r"\b(ai engineer|artificial intelligence engineer|generative ai|genai|agentic ai|llm engineer|ai automation engineer)\b", "Applied AI / GenAI"),
    (r"\b(data analyst|reporting analyst|analytics analyst)\b", "Data Analyst"),
    (r"\b(business analyst|mis analyst|mis executive)\b", "Business Analyst / MIS"),
    (r"\b(python developer|backend developer|back-end developer|software engineer|software developer|api developer)\b", "Software / Python Developer"),
    (r"\b(quality engineer|quality analyst|test engineer|qa engineer)\b", "Quality / Test Engineer"),
]

SOCIAL_NOTIFICATION_PATTERNS = [
    r"\bshared their thoughts\b", r"\bshared a post\b",
    r"\bsuggested for you\b.*\bshared\b", r"\bpeople you may know\b",
    r"\bcommented on\b", r"\breacted to\b",
    r"\bcelebrated\b.*\bwork anniversary\b", r"\bnetwork conversations\b",
]
JOB_INTENT_PATTERNS = [
    r"\bhiring\b", r"\bwe(?:'|’|â€™)re hiring\b", r"\bjob alert\b",
    r"\bjob opening(?:s)?\b", r"\bopenings?\b", r"\bvacanc(?:y|ies)\b",
    r"\bcareer opportunit(?:y|ies)\b", r"\bjob opportunit(?:y|ies)\b",
    r"\bapply now\b", r"\bapply for\b", r"\bposition available\b",
    r"\brecruit(?:ment|er|ing)\b", r"\bjoin our team\b",
    r"\bjob description\b", r"\brole overview\b", r"\beasy apply\b",
    r"\bresponsibilities\b.*\brequirements\b",
]
DETAIL_PATTERNS = (
    r"\b(job description|responsibilities|what you(?:'|’|â€™)ll do|role description)\b",
    r"\b(requirements|qualifications|must have|skills required)\b",
    r"\b(experience|years of experience)\b",
    r"\b(location|work mode|remote|hybrid)\b",
    r"\b(apply|application link|apply here|easy apply)\b",
)
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
NON_VACANCY_PATHS = (
    "/comm/jobs/alerts", "/jobs/search", "/jobs/search-results",
    "/comm/feed/", "/feed/update/", "/preload/guideoverlay",
    "/comm/my-network/", "/messaging/",
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _has_role(text: str) -> bool:
    return any(re.search(pattern, text or "", re.I) for pattern, _ in ROLE_PATTERNS)


def _urls(body: str) -> list[str]:
    return [u.rstrip(".,;!?)]}") for u in URL_RE.findall(body or "")]


def _is_generic_url(url: str) -> bool:
    path = (urlparse(url).path or "").lower()
    return any(part in path for part in NON_VACANCY_PATHS)


def _specific_vacancy_evidence(body: str) -> bool:
    cues = sum(bool(re.search(pattern, body or "", re.I)) for pattern in DETAIL_PATTERNS)
    direct_link = any(not _is_generic_url(url) for url in _urls(body))
    substantial_description = len(_clean(body)) >= 300 and cues >= 2
    return (direct_link and cues >= 1) or substantial_description


def is_likely_job_email(subject: str, sender: str, body: str) -> bool:
    """Filter social digests and require evidence of a specific vacancy."""
    subject, body = _clean(subject), body or ""
    combined = f"{subject}\n{body}"
    sender_lower = (sender or "").lower()
    if any(re.search(pattern, subject, re.I) for pattern in SOCIAL_NOTIFICATION_PATTERNS):
        return False
    if ("linkedin" in sender_lower or "network conversations" in body.lower()) and re.search(
        r"\b(shared a post|shared their thoughts|suggested for you|network conversations)\b", combined, re.I
    ):
        return False
    has_intent = any(re.search(pattern, combined, re.I) for pattern in JOB_INTENT_PATTERNS)
    if not has_intent or not _has_role(subject) and not _has_role(body):
        return False
    return _specific_vacancy_evidence(body)


def _extract_company(subject: str, body: str) -> str:
    text = f"{subject}\n{body}"
    patterns = [
        r"(?:company|employer|organization)\s*[:\-]\s*([^\n|,;]{2,80})",
        r"\b(?:at|with)\s+([A-Z][A-Za-z0-9&.' -]{1,50}?)(?=\s+(?:is hiring|is looking|for the role|is seeking|to join)|[.,\n]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = _clean(match.group(1)).strip(" .-")
            if candidate and candidate.lower() not in {"the role", "our team", "unknown company"}:
                return candidate
    match = re.match(r"^\s*([A-Z][A-Za-z0-9&.' -]{1,50}?)\s+(?:hiring|recruiting)\s*:", subject or "")
    return _clean(match.group(1)).strip(" .-") if match else "Unknown company"


def _select_application_url(body: str) -> str:
    return next((url for url in _urls(body) if not _is_generic_url(url)), "")


def parse_job_email(subject: str, sender: str, date: str, body: str, message_id: str = "") -> dict:
    subject = _clean(subject)
    body = body or ""
    text = f"{subject}\n{body}"
    return {
        "title": subject[:140] if subject else "Unknown role",
        "company": _extract_company(subject, body),
        "location": "",
        "application_url": _select_application_url(body),
        "description": _clean(body)[:12000],
        "source": "Email",
        "email_message_id": message_id,
        "raw_email": text[:20000],
        "email_sender": sender,
        "email_date": date,
        "classification": "likely_vacancy" if is_likely_job_email(subject, sender, body) else "needs_verification",
    }
