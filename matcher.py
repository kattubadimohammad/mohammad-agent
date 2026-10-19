from pathlib import Path
import re
SKILLS=['python','sql','excel','power bi','tableau','pandas','numpy','scikit-learn','machine learning','deep learning','nlp','xgboost','tensorflow','pytorch','data engineering','etl','elt','data pipeline','airflow','dbt','snowflake','azure','aws','gcp','spark','databricks','streamlit','api','llm','rag','generative ai','agentic ai','langchain','vector database','prompt engineering','statistics','forecasting','dashboard','reporting','stakeholder management']
def normalize(text: str) -> str: return re.sub(r'\\s+',' ',(text or '').lower())
def score_job(job: dict, selected_roles: list[str], resume_path: str):
    desc=normalize(' '.join(str(job.get(k) or '') for k in ('title','description','raw_email')))
    p=Path(resume_path); resume=normalize(p.read_text(encoding='utf-8',errors='ignore') if p.exists() else '')
    found=[s for s in SKILLS if s in desc]; matched=[s for s in found if s in resume]; missing=[s for s in found if s not in resume]
    role_match=any(r.lower() in desc for r in selected_roles)
    skill_score=round(100*len(matched)/max(1,len(found))); score=round(skill_score*0.7+(30 if role_match else 0))
    if not found: score=30 if role_match else 0
    return min(100,score),', '.join(matched),', '.join(missing)
