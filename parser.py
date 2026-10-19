import re

ROLE_PATTERNS = [
    (r"\b(data engineer|analytics engineer|etl engineer)\b", "Data Engineer"),
    (r"\b(data scientist|applied scientist)\b", "Data Scientist"),
    (r"\b(ai\s*/?\s*ml engineer|machine learning engineer|ml engineer)\b", "AI/ML Engineer"),
    (r"\b(generative ai|genai|agentic ai|llm engineer|ai automation engineer)\b", "Applied AI / GenAI"),
    (r"\b(data analyst|reporting analyst|analytics analyst)\b", "Data Analyst"),
    (r"\b(business analyst|mis analyst|mis executive)\b", "Business Analyst / MIS"),
]

# LinkedIn network-conversation digests frequently contain job-related words in
# posts, but they are not themselves job vacancies.
SOCIAL_NOTIFICATION_PATTERNS = [
    r"\bshared their thoughts\b",
    r"\bshared a post\b",
    r"\bsuggested for you\b.*\bshared\b",
    r"\bpeople you may know\b",
    r"\bcommented on\b",
    r"\breacted to\b",
    r"\bcelebrated\b.*\bwork anniversary\b",
    r"\bnetwork conversations\b",
]

JOB_INTENT_PATTERNS = [
    r"\bhiring\b",
    r"\bwe(?:'|’)re hiring\b",
    r"\bjob alert\b",
    r"\bjob opening(?:s)?\b",
    r"\bopenings?\b",
    r"\bvacanc(?:y|ies)\b",
    r"\bcareer opportunit(?:y|ies)\b",
    r"\bjob opportunit(?:y|ies)\b",
    r"\bapply now\b",
    r"\bapply for\b",
    r"\bposition available\b",
    r"\brecruit(?:ment|er|ing)\b",
    r"\bjoin our team\b",
    r"\bjob description\b",
    r"\brole overview\b",
    r"\bresponsibilities\b.*\brequirements\b",
]

def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def _has_role(text: str) -> bool:
    return any(re.search(pattern, text or "", re.I) for pattern, _ in ROLE_PATTERNS)

def is_likely_job_email(subject: str, sender: str, body: str) -> bool:
    """Conservatively identify vacancy emails and reject social activity digests."""
    subject = _clean(subject)
    body = body or ""
    combined = f"{subject}\n{body}"
    sender_lower = (sender or "").lower()

    # Reject activity digests even when a post inside the digest mentions jobs.
    if any(re.search(pattern, subject, re.I) for pattern in SOCIAL_NOTIFICATION_PATTERNS):
        return False
    if (
        ("linkedin" in sender_lower or "network conversations" in body.lower())
        and re.search(
            r"\b(shared a post|shared their thoughts|suggested for you|network conversations)\b",
            combined,
            re.I,
        )
    ):
        return False

    has_job_intent = any(re.search(pattern, combined, re.I) for pattern in JOB_INTENT_PATTERNS)
    subject_has_role = _has_role(subject)
    body_has_role = _has_role(body)

    # A role mention by itself is not enough: it may be an interview story,
    # newsletter, or social post. Require vacancy language or job-description
    # evidence before importing it.
    detail_cues = sum(
        bool(re.search(pattern, body, re.I))
        for pattern in (
            r"\b(job description|responsibilities|what you(?:'|’)ll do)\b",
            r"\b(requirements|qualifications|must have|skills required)\b",
            r"\b(experience|years of experience)\b",
            r"\b(location|work mode|remote|hybrid)\b",
            r"\b(apply|application link|apply here)\b",
        )
    )
    return has_job_intent and (subject_has_role or body_has_role or detail_cues >= 2)

def parse_job_email(
    subject: str,
    sender: str,
    date: str,
    body: str,
    message_id: str = "",
) -> dict:
    subject = _clean(subject)
    body = body or ""
    text = f"{subject}\n{body}"
    title = subject[:140] if subject else "Unknown role"

    # Use the subject to choose a normalized role, not the entire email footer.
    normalized_role = next(
        (normalized for pattern, normalized in ROLE_PATTERNS if re.search(pattern, subject, re.I)),
        "",
    )
    if title.lower() in {"", "unknown role"}:
        title = normalized_role or "Unknown role"

    company = "Unknown company"
    company_patterns = [
        r"(?:company|employer|organization)\s*[:\-]\s*([^\n|,;]{2,80})",
        r"\bat\s+([A-Z][A-Za-z0-9&.' -]{1,60})(?=\s+(?:is hiring|is looking|for the role)|[.,\n]|$)",
    ]
    for pattern in company_patterns:
        match = re.search(pattern, subject, re.I) or re.search(pattern, body, re.I)
        if match:
            candidate = _clean(match.group(1)).strip(" .-")
            if candidate and candidate.lower() not in {"the role", "our team"}:
                company = candidate
                break

    url_match = re.search(r"https?://[^\s<>\"')\]]+", body, re.I)
    url = url_match.group(0).rstrip(".,;") if url_match else ""

    return {
        "title": title,
        "company": company,
        "location": "",
        "application_url": url,
        "description": _clean(body)[:12000],
        "source": "Email",
        "email_message_id": message_id,
        "raw_email": text[:20000],
        "email_sender": sender,
        "email_date": date,
    }
