from pathlib import Path
import re

SKILLS = [
    "python", "sql", "excel", "power bi", "tableau", "pandas", "numpy",
    "scikit-learn", "machine learning", "deep learning", "nlp", "xgboost",
    "tensorflow", "pytorch", "data engineering", "etl", "elt", "data pipeline",
    "airflow", "dbt", "snowflake", "azure", "aws", "gcp", "spark", "databricks",
    "streamlit", "api", "llm", "rag", "generative ai", "agentic ai", "langchain",
    "vector database", "prompt engineering", "statistics", "forecasting",
    "dashboard", "reporting", "stakeholder management",
]

ROLE_ALIASES = {
    "Data Engineer": ("data engineer", "analytics engineer", "etl engineer"),
    "Data Scientist": ("data scientist", "applied scientist"),
    "AI/ML Engineer": ("ai/ml engineer", "ai ml engineer", "machine learning engineer", "ml engineer"),
    "Applied AI / GenAI": ("generative ai", "genai", "agentic ai", "llm engineer", "ai automation engineer"),
    "Data Analyst": ("data analyst", "reporting analyst", "analytics analyst"),
    "Business Analyst / MIS": ("business analyst", "mis analyst", "mis executive"),
}

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())

def score_job(job: dict, selected_roles: list[str], resume_path: str):
    """Score against vacancy-specific text only; never mine raw email footers."""
    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    job_text = normalize(f"{title}\n{description}")
    resume_file = Path(resume_path)
    resume = normalize(
        resume_file.read_text(encoding="utf-8", errors="ignore")
        if resume_file.exists()
        else ""
    )

    found = [skill for skill in SKILLS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", job_text)]
    matched = [skill for skill in found if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", resume)]
    missing = [skill for skill in found if skill not in matched]

    role_match = False
    for selected_role in selected_roles:
        aliases = ROLE_ALIASES.get(selected_role, (selected_role.lower(),))
        if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", job_text) for alias in aliases):
            role_match = True
            break

    skill_score = round(100 * len(matched) / len(found)) if found else 0
    score = round(skill_score * 0.7 + (30 if role_match else 0))

    # Sparse subjects and short snippets are not enough evidence for a perfect
    # score. A 100% match should require several explicit skill requirements.
    if len(found) < 5 or len(description.strip()) < 300:
        score = min(score, 85)
    return min(max(score, 0), 100), ", ".join(matched), ", ".join(missing)
