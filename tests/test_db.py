from db import init_db, upsert_job, list_jobs, update_job_status

def test_dedupes_same_title_company(tmp_path):
    db=str(tmp_path/'jobs.sqlite3'); init_db(db)
    job={'title':'Data Analyst','company':'Example Co','source':'Manual','description':'SQL'}
    assert upsert_job(db,job) is True
    assert upsert_job(db,job) is False
    assert len(list_jobs(db)) == 1
    update_job_status(db,1,'Approved')
    assert list_jobs(db)[0]['status'] == 'Approved'
