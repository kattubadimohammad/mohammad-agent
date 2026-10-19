from __future__ import annotations
import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from db import init_db, list_jobs, update_job_status, upsert_job, add_audit
from gmail_client import fetch_job_emails, GmailSetupError
from parser import parse_job_email, is_likely_job_email
from matcher import score_job
from resume_builder import build_resume_variant

load_dotenv()
DB_PATH = os.getenv('DB_PATH', 'data/job_agent.sqlite3')
MASTER_RESUME = os.getenv('MASTER_RESUME_PATH', 'resumes/master_resume.md')
init_db(DB_PATH)
st.set_page_config(page_title='Mohammad Agent', page_icon='🧭', layout='wide')
st.title('🧭 Mohammad Agent')
st.caption('Personal AI Job Application Agent — discover → extract → match → review → approve. It does not submit applications automatically.')
roles = ['Data Engineer', 'Data Scientist', 'AI/ML Engineer', 'Applied AI / GenAI', 'Data Analyst', 'Business Analyst / MIS']
with st.sidebar:
    st.header('Settings')
    selected_roles = [r for r in roles if st.checkbox(r, value=True, key='role_'+r)]
    st.divider()
    st.write('Gmail setup')
    st.caption('Place your Google OAuth Desktop app file at credentials.json in the project folder. Never commit it to Git.')
    max_emails = st.number_input('Maximum emails to scan', min_value=5, max_value=200, value=30, step=5)

tab1, tab2, tab3, tab4 = st.tabs(['Dashboard', 'Import from Gmail', 'Review jobs', 'Resume versions'])

with tab1:
    jobs = list_jobs(DB_PATH)
    counts = {}
    for job_item in jobs:
        counts[job_item['status']] = counts.get(job_item['status'], 0) + 1
    cols = st.columns(4)
    cols[0].metric('Jobs found', len(jobs))
    cols[1].metric('Needs review', counts.get('New', 0) + counts.get('Review', 0))
    cols[2].metric('Approved', counts.get('Approved', 0))
    cols[3].metric('Applied', counts.get('Applied', 0))
    if jobs:
        st.dataframe(
            [{'Title': j['title'], 'Company': j['company'], 'Location': j['location'],
              'Match %': j['match_score'], 'Status': j['status'], 'Source': j['source']}
             for j in jobs[:30]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info('No jobs yet. Import emails or add a job manually under Review jobs.')

with tab2:
    st.subheader('Import job emails')
    st.write("Connect with Google's local OAuth flow. Your browser opens for consent; credentials remain on your computer.")
    if st.button('Connect to Gmail and import emails', type='primary'):
        try:
            with st.spinner('Reading recent job-related emails…'):
                emails = fetch_job_emails(max_results=int(max_emails))
                imported = 0
                skipped = 0
                for email in emails:
                    if not is_likely_job_email(email['subject'], email['sender'], email['body']):
                        skipped += 1
                        continue
                    item = parse_job_email(
                        email['subject'], email['sender'], email['date'],
                        email['body'], email['message_id'],
                    )
                    if not item.get('title') or item.get('title') == 'Unknown role':
                        skipped += 1
                        continue
                    item['source'] = 'Gmail'
                    item['email_message_id'] = email['message_id']
                    item['raw_email'] = (email['subject'] + '\n\n' + email['body'])[:20000]
                    item['match_score'], item['matched_skills'], item['missing_skills'] = score_job(
                        item, selected_roles, MASTER_RESUME
                    )
                    imported += int(upsert_job(DB_PATH, item))
                add_audit(
                    DB_PATH, 'gmail_import',
                    f'Fetched {len(emails)} emails; new jobs {imported}; skipped {skipped}',
                )
            st.success(
                f'Scanned {len(emails)} emails. Added {imported} new jobs; '
                f'skipped {skipped} non-job or unrecognized messages. Existing jobs are deduplicated.'
            )
        except GmailSetupError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f'Import failed: {exc}. Check README.md and Google OAuth setup.')

with tab3:
    st.subheader('Review and approve')
    all_jobs = list_jobs(DB_PATH)
    # Keep completed/rejected items in the database and Dashboard, but do not
    # put them back into the pending-review selector.
    review_jobs = [j for j in all_jobs if j['status'] in {'New', 'Review', 'Hold'}]
    if review_jobs:
        labels = {
            f"{j['id']} · {j['title']} — {j['company']} ({j['match_score']}%) [{j['status']}]": j['id']
            for j in review_jobs
        }
        label = st.selectbox('Choose a job', list(labels.keys()), key='review_job_select')
        job = next(j for j in review_jobs if j['id'] == labels[label])
        st.markdown(f"### {job['title']} — {job['company']}")
        st.write(f"Location: {job['location'] or 'Not specified'} | Source: {job['source']}")
        st.write(f"Application link: {job['application_url'] or 'Not found — verify manually'}")
        st.progress(min(max(int(job['match_score'] or 0), 0), 100))
        st.write(f"Resume match: {job['match_score']}%")
        if job['matched_skills']:
            st.write('Matched keywords: ' + job['matched_skills'])
        if job['missing_skills']:
            st.write('Keywords not found in resume: ' + job['missing_skills'])
        with st.expander('Extracted job description / email'):
            st.text_area(
                'Details', value=job['description'] or job['raw_email'] or '',
                height=220, disabled=True, key=f"details_{job['id']}",
            )
        st.warning('Approval records your decision to proceed. It does not submit anything.')
        c1, c2, c3, c4 = st.columns(4)
        if c1.button('Approve', key=f"approve_{job['id']}"):
            update_job_status(DB_PATH, job['id'], 'Approved')
            add_audit(DB_PATH, 'approve_job', f"Job {job['id']} approved")
            st.rerun()
        if c2.button('Mark applied', key=f"applied_{job['id']}"):
            update_job_status(DB_PATH, job['id'], 'Applied')
            add_audit(DB_PATH, 'mark_applied', f"Job {job['id']} marked applied by user")
            st.rerun()
        if c3.button('Hold', key=f"hold_{job['id']}"):
            update_job_status(DB_PATH, job['id'], 'Hold')
            add_audit(DB_PATH, 'hold_job', f"Job {job['id']} put on hold")
            st.rerun()
        if c4.button('Reject', key=f"reject_{job['id']}"):
            update_job_status(DB_PATH, job['id'], 'Rejected')
            add_audit(DB_PATH, 'reject_job', f"Job {job['id']} rejected")
            st.rerun()
    else:
        st.success('No pending jobs to review. Import more emails or add a genuine vacancy below.')

    with st.expander('Add a job manually'):
        with st.form('manual_job'):
            title = st.text_input('Job title')
            company = st.text_input('Company')
            location = st.text_input('Location', value='India / Remote')
            url = st.text_input('Application URL')
            description = st.text_area('Job description')
            submitted = st.form_submit_button('Save job')
            if submitted:
                if not title.strip() or not company.strip():
                    st.error('Job title and company are required.')
                else:
                    item = {
                        'title': title.strip(), 'company': company.strip(),
                        'location': location.strip(), 'application_url': url.strip(),
                        'description': description, 'source': 'Manual',
                        'raw_email': description, 'email_message_id': None,
                    }
                    item['match_score'], item['matched_skills'], item['missing_skills'] = score_job(
                        item, selected_roles, MASTER_RESUME
                    )
                    upsert_job(DB_PATH, item)
                    add_audit(DB_PATH, 'manual_job', f"Manually added {title} at {company}")
                    st.success('Saved (duplicate detection applied).')
                    st.rerun()

with tab4:
    st.subheader('Master resume and tailored versions')
    st.write('Use only verified roles, dates, skills, projects and metrics. The generator does not invent achievements.')
    p = Path(MASTER_RESUME)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(
            '# Master Resume\n\n## Professional Summary\n[Add a truthful summary]\n\n'
            '## Skills\n[Add verified skills]\n\n## Experience\n'
            '[Employer, title, dates, responsibilities and verified achievements]\n\n'
            '## Projects\n[Projects and accurate metrics]\n',
            encoding='utf-8',
        )
    master = p.read_text(encoding='utf-8')
    edited = st.text_area('Master resume (Markdown)', value=master, height=300)
    if st.button('Save master resume'):
        p.write_text(edited, encoding='utf-8')
        add_audit(DB_PATH, 'save_resume', 'Master resume updated')
        st.success(f'Saved to {p}')
    a, b = st.columns(2)
    if a.button('Generate Data / AI-ML version'):
        out = build_resume_variant(edited, 'data_ai_ml', 'resumes/data_ai_ml_resume.md')
        st.success(f'Created {out}')
        st.code(Path(out).read_text(encoding='utf-8'), language='markdown')
    if b.button('Generate GenAI / Agentic AI version'):
        out = build_resume_variant(edited, 'genai_agentic', 'resumes/genai_agentic_resume.md')
        st.success(f'Created {out}')
        st.code(Path(out).read_text(encoding='utf-8'), language='markdown')
