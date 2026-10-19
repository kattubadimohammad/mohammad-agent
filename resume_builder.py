from pathlib import Path
SECTIONS={'data_ai_ml':{'heading':'Data Engineering, Analytics & AI/ML Resume','keywords':['Python','SQL','data pipelines','analytics','machine learning','forecasting','Power BI','data quality']},'genai_agentic':{'heading':'Generative AI & Agentic AI Resume','keywords':['Python','LLMs','RAG','agentic workflows','API integration','evaluation','automation','data processing']}}
def build_resume_variant(master_text: str, variant: str, output_path: str) -> str:
    if variant not in SECTIONS: raise ValueError('Unknown resume variant')
    config=SECTIONS[variant]
    content=f"# {config['heading']}\n\n> Draft generated from the master resume. Verify every claim and remove any skill you cannot demonstrate.\n\n## Master Resume Content\n\n{master_text.strip()}\n\n## Role-specific keywords to consider (include only when accurate)\n\n"+'\n'.join(f'- {k}' for k in config['keywords'])+'\n'
    path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf-8'); return str(path)
