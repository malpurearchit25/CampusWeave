import pytest
from db import query,transaction,execute,call
from scheduler import generate

@pytest.mark.parametrize('route',['/','/academic/faculty','/academic/courses','/academic/divisions','/academic/rooms','/academic/course_offerings','/academic/faculty_courses','/academic/faculty_unavailability','/academic/time_slots','/academic/departments','/generate','/analytics','/lab','/guide'])
def test_pages_render(client,route):assert client.get(route).status_code==200

def test_csrf_rejects_mutation(client):assert client.post('/academic/departments',data={'department_name':'CSRF'}).status_code==400

def test_authentication_required(client):
    with client.session_transaction() as s:s.clear()
    assert client.get('/').status_code==302
    client.get('/login')
    with client.session_transaction() as s:token=s['csrf']
    response=client.post('/login',data={'csrf':token,'username':'admin','password':'CampusDemo!2026'})
    assert response.status_code==302
    assert client.get('/').status_code==200

def test_xss_output_is_escaped(client):
    with transaction() as cn:execute(cn,"INSERT INTO departments(department_name) VALUES(%s)",('<script>alert(1)</script>',))
    body=client.get('/academic/departments').data
    assert b'&lt;script&gt;' in body and b'<script>alert(1)</script>' not in body

def test_catalog_create_edit_delete(client):
    client.post('/academic/departments',data={'csrf':'test-csrf','department_name':'Test department'})
    rid=query("SELECT department_id FROM departments WHERE department_name='Test department'")[0]['department_id']
    client.post('/academic/departments',data={'csrf':'test-csrf','id':rid,'department_name':'Updated department'})
    assert query('SELECT department_name FROM departments WHERE department_id=%s',(rid,))[0]['department_name']=='Updated department'
    client.post('/academic/departments',data={'csrf':'test-csrf','action':'delete','id':rid})
    assert not query('SELECT * FROM departments WHERE department_id=%s',(rid,))

def test_live_savepoint_experiment_leaves_no_rows(client):
    before=query('SELECT COUNT(*) n FROM departments')[0]['n']
    response=client.post('/lab',data={'csrf':'test-csrf'})
    assert response.status_code==200 and b'No experiment rows remain' in response.data
    assert query('SELECT COUNT(*) n FROM departments')[0]['n']==before

def test_publish_route_calls_procedure_and_audit(client):
    run=generate(1,'2026-27',3,1)[0]
    response=client.post(f'/timetable/{run}/publish',data={'csrf':'test-csrf'},follow_redirects=True)
    assert response.status_code==200 and b'All checks passed' in response.data
    assert query('SELECT COUNT(*) n FROM approval_history')[0]['n']==1

def test_csv_export(client):
    run=generate(1,'2026-27',3,1)[0]
    response=client.get(f'/timetable/{run}/export.csv')
    assert response.status_code==200 and 'text/csv' in response.content_type
    assert len(response.data.decode().splitlines())==33

def test_missing_run_404(client):assert client.get('/timetable/999999').status_code==404

def test_analytics_excludes_draft(client):
    generate(1,'2026-27',3,1)
    body=client.get('/analytics').data
    assert b'0 / 16 h' in body
