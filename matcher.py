from pathlib import Path
import re

# Skills are deliberately explicit so users can audit why a match was scored.
SKILLS = [
    "python", "sql", "excel", "power bi", "tableau", "pandas", "numpy",
    "scikit-learn", "machine learning", "deep learning", "nlp", "xgboost",
    "tensorflow", "pytorch", "data engineering", "etl", "elt", "data pipeline",
    "airflow", "dbt", "snowflake", "azure", "aws", "gcp", "spark", "databricks",
    "streamlit", "rest api", "restful api", "api", "oop", "object-oriented programming",
    "data structures", "algorithms", "unit testing", "pytest", "testing", "backend",
    "fastapi", "flask", "django", "postgresql", "mysql", "mongodb", "nosql",
    "docker", "kubernetes", "ci/cd", "github actions", "azure devops", "llm", "rag",
    "generative ai", "agentic ai", "langchain", "vector database", "prompt engineering",
    "statistics", "forecasting", "dashboard", "reporting", "stakeholder management",
    "distributed systems", "microservices", "performance optimization", "code review",
]

ROLE_ALIASES = {
    "Data Engineer": ("data engineer", "analytics engineer", "etl engineer"),
    "Data Scientist": ("data scientist", "applied scientist"),
    "AI/ML Engineer": ("ai/ml engineer", "ai ml engineer", "machine learning engineer", "ml engineer"),
    "Applied AI / GenAI": ("ai engineer", "artificial intelligence engineer", "generative ai", "genai", "agentic ai", "llm engineer", "ai automation engineer"),
    "Data Analyst": ("data analyst", "reporting analyst", "analytics analyst"),
    "Business Analyst / MIS": ("business analyst", "mis analyst", "mis executive"),
    "Software / Python Developer": ("python developer", "backend developer", "back-end developer", "software engineer", "software developer", "api developer"),
    "Quality / Test Engineer": ("quality engineer", "quality analyst", "test engineer", "qa engineer"),
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _contains(text: str, phrase: str) -> bool:
    # Allow common punctuation variants for phrases such as RESTful API and CI/CD.
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def score_job(job: dict, selected_roles: list[str], resume_path: str):
    """Score only the vacancy title/description, not email footers or tracking URLs."""
    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    job_text = normalize(f"{title}\n{description}")
    resume_file = Path(resume_path)
    resume = normalize(resume_file.read_text(encoding="utf-8", errors="ignore") if resume_file.exists() else "")

    found = [skill for skill in SKILLS if _contains(job_text, skill)]
    matched = [skill for skill in found if _contains(resume, skill)]
    missing = [skill for skill in found if skill not in matched]

    role_match = any(
        _contains(job_text, alias)
        for role in selected_roles
        for alias in ROLE_ALIASES.get(role, (role.lower(),))
    )
    skill_score = round(100 * len(matched) / len(found)) if found else 0
    score = round(skill_score * 0.7 + (30 if role_match else 0))
    # Short/low-evidence descriptions cannot be scored as a near-perfect fit.
    if len(found) < 3 or len(description.strip()) < 300:
        score = min(score, 85)
    return min(max(score, 0), 100), ", ".join(matched), ", ".join(missing)
