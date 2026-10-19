from pathlib import Path

from matcher import score_job
from parser import is_likely_job_email, parse_job_email


def test_rejects_linkedin_activity_digest_even_when_post_mentions_a_job():
    subject = "Suggested for you Manoj Kumar Sethy shared a post: Swiggy Business Analyst interview"
    body = "Recently interviewed for a Business Analyst role. Read more: https://www.linkedin.com/comm/feed/update/"
    assert not is_likely_job_email(subject, "messages-noreply@linkedin.com", body)


def test_rejects_linkedin_network_conversation_notification():
    subject = "Manoj Kumar Sethy and others share their thoughts on LinkedIn"
    body = "Prasad shared a post about multiple openings at Flipkart. Read more on LinkedIn."
    assert not is_likely_job_email(subject, "messages-noreply@linkedin.com", body)


def test_accepts_clear_job_alert():
    subject = "Mphasis hiring: AI/ML Engineer"
    body = (
        "Job description: Build machine learning services. Responsibilities include model deployment. "
        "Requirements: Python, SQL, machine learning. Experience: 2+ years. "
        "Location: Bengaluru. Apply here: https://example.com/jobs/123"
    )
    assert is_likely_job_email(subject, "careers@example.com", body)
    job = parse_job_email(subject, "careers@example.com", "2026-10-19", body, "msg-1")
    assert job["title"] == subject
    assert job["application_url"] == "https://example.com/jobs/123"


def test_short_snippet_cannot_receive_perfect_match(tmp_path: Path):
    resume = tmp_path / "resume.md"
    resume.write_text("SQL Excel Power BI Python data analyst", encoding="utf-8")
    job = {
        "title": "Data Analyst",
        "description": "SQL, Excel, Power BI",
        # Raw email footers must not influence score.
        "raw_email": "Python Python Python SQL Excel Power BI and every skill imaginable",
    }
    score, matched, missing = score_job(job, ["Data Analyst"], str(resume))
    assert score <= 85
    assert "python" not in matched
