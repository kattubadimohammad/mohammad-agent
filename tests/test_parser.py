from parser import parse_job_email

def test_parse_job_email_extracts_role_and_url():
    item = parse_job_email('Data Engineer opening','recruiter@example.com','Mon, 1 Jan 2026 10:00:00 +0000','We are hiring a Data Engineer. Apply here https://example.com/jobs/123')
    assert item['title'] == 'Data Engineer opening'
    assert item['application_url'].startswith('https://example.com/jobs/123')
