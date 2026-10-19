# Mohammad Agent — Personal AI Job Application Agent

A local-first Python and Streamlit MVP for discovering job opportunities from Gmail, extracting vacancy details, matching jobs against a master resume, detecting duplicates, and tracking applications with a human approval step.

> **Safety:** This MVP does not submit applications or send email. Gmail integration uses read-only OAuth permission. Review every job, link, score, and resume before applying.

## Features

- Gmail API integration with OAuth 2.0 (`gmail.readonly`).
- Job email extraction for role title, company, description and application link.
- SQLite database for vacancies and an audit trail.
- Duplicate detection using application URL, or title + company when no URL exists.
- Transparent heuristic keyword match score with matched and missing keywords.
- Streamlit dashboard to review jobs and track New, Approved, Applied, Hold and Rejected states.
- Master resume workflow plus Data/AI-ML and GenAI/Agentic AI draft variants.

## Project setup

Requirements: Python 3.10+ and a Google account.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Open the local Streamlit URL printed in the terminal.

### Gmail OAuth setup

1. Open [Google Cloud Console](https://console.cloud.google.com/), create or select a project, and enable **Gmail API**.
2. Configure the OAuth consent screen. Add your own account as a test user if the app is in Testing.
3. Create an OAuth client ID for a **Desktop app** and download its JSON.
4. Place that file in the project root as `credentials.json`.
5. In the app, choose **Import from Gmail** and connect. Review Google's consent prompt and allow read-only access.
6. Keep `credentials.json`, `token.json`, `.env`, and the local database private. Never commit them to GitHub.

## Resume workflow

Edit `resumes/master_resume.md` with verified skills, experience, dates, projects and metrics. Generate the Data/AI-ML or GenAI/Agentic AI version from the app. The variants only add keyword suggestions; include a keyword only if you can substantiate it. They are Markdown drafts and must be reviewed before use.

## Matching-score limitations

The current score is a simple keyword heuristic, not a probability of receiving an interview. It does not fully understand seniority, context, or nuanced job requirements. Use it to sort opportunities, not to make final decisions.

## Tests

```powershell
pytest -q
```

## Initial project files

Upload the remaining files from the provided project ZIP while preserving the paths:

- `app.py`
- `db.py`
- `gmail_client.py`
- `matcher.py`
- `parser.py`
- `resume_builder.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `tests/test_parser.py`
- `tests/test_db.py`
- `resumes/master_resume.md`

The README is a start here guide; ensure the complete project files are uploaded before running from a fresh clone.
