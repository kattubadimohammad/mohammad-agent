from parser import is_likely_job_email, parse_job_email


def test_recognizes_python_developer_vacancy_and_company():
    body = (
        "Role Description: Python Developer. Responsibilities include building RESTful APIs and database queries. "
        "Qualifications: Python, OOP, SQL, testing. Experience: 2 years. Location: India Remote. "
        "Apply here: https://example.com/jobs/python-123"
    )
    assert is_likely_job_email("Python Developer job alert at Rackloom", "jobs@example.com", body)
    job = parse_job_email("Python Developer job alert at Rackloom", "jobs@example.com", "today", body)
    assert job["company"] == "Rackloom"
    assert job["application_url"] == "https://example.com/jobs/python-123"
    assert job["classification"] == "likely_vacancy"


def test_does_not_choose_generic_linkedin_alert_as_application_url():
    body = "Python Developer job alert. Responsibilities include Python development. https://www.linkedin.com/comm/jobs/alerts?foo=bar"
    job = parse_job_email("Python Developer job alert", "linkedin@example.com", "today", body)
    assert job["application_url"] == ""


def test_accepts_ai_engineer_title_alias():
    body = "Job description: AI Engineer. Responsibilities include building AI services. Requirements: Python, LLM, RAG. Location: Remote. Apply here https://example.com/ai-role"
    assert is_likely_job_email("AI Engineer", "jobs@example.com", body)
