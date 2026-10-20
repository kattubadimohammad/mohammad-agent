from matcher import score_job


def test_python_developer_alias_and_backend_skills_match(tmp_path):
    resume = tmp_path / "resume.md"
    resume.write_text("Python developer with RESTful API, SQL, OOP, pytest and FastAPI experience", encoding="utf-8")
    job = {
        "title": "Python Developer at Rackloom",
        "description": "Build RESTful API services using Python, SQL, OOP, pytest, FastAPI and Docker. " * 5,
        "raw_email": "Footer says machine learning machine learning machine learning",
    }
    score, matched, missing = score_job(job, ["Software / Python Developer"], str(resume))
    assert score > 50
    assert "python" in matched
    assert "restful api" in matched
    assert "machine learning" not in matched
