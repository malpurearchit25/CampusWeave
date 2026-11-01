import json,os,uuid
from pathlib import Path
import pytest
from pymongo import MongoClient
from db import transaction,call,query
from scheduler import generate
from warehouse import load_mart,olap
from syllabus_lab import closure,minimal_cover,synthesize_3nf,conflict_graph,view_serial_order,run_theory_experiments

def test_fd_synthesis_and_parallel_reconstruction():
    evidence=run_theory_experiments()
    assert evidence['fd_closure_A']==list('ABCD')
    assert evidence['parallel_matches_serial'] and evidence['fourth_normal_form']['lossless']

def test_view_checker_distinguishes_multiple_writes_of_same_transaction():
    schedule=[('T1','W','X'),('T2','R','X'),('T1','W','X')]
    assert view_serial_order(schedule) is None

def test_closure_handles_cycles_without_looping():
    assert closure({'A'},[({'A'},{'B'}),({'B'},{'A'}),({'B'},{'C'})])==set('ABC')

def test_warehouse_idempotent_and_excludes_drafts():
    run=generate(1,'2026-27',3,1)[0]
    assert load_mart()==0
    with transaction() as cn:call(cn,'sp_publish_run',(run,1))
    assert load_mart()==32 and load_mart()==32
    grand=next(r for r in olap() if r['academic_year'] is None)
    assert grand['hours']==32

def test_function_reports_run_hours():
    run=generate(1,'2026-27',3,1)[0]
    assert query('SELECT fn_run_hours(%s) hours',(run,))[0]['hours']==32

@pytest.mark.parametrize('route',['/lab/theory','/lab/warehouse'])
def test_syllabus_pages(client,route):assert client.get(route).status_code==200

def test_actual_mongo_crud_and_web_connectivity(client,monkeypatch):
    root=Path(__file__).resolve().parents[1]
    password=os.getenv('MONGO_ADMIN_PASSWORD') or json.loads((root/'runtime/mongo-admin.json').read_text())['password']
    uri=f'mongodb://campus_admin:{password}@127.0.0.1:27018/admin';name='campusweave_test_'+uuid.uuid4().hex[:10]
    monkeypatch.setenv('MONGO_URI',uri);monkeypatch.setenv('MONGO_DB',name)
    from mongo_store import feedback_list
    try:
        response=client.post('/lab/mongodb',data={'csrf':'test-csrf','course':'DBMS','rating':'5','note':'Good spacing','tags':'morning, theory'})
        assert response.status_code==302
        notes,summary=feedback_list();assert len(notes)==1 and summary[0]['average']==5
        oid=str(notes[0]['_id'])
        client.post('/lab/mongodb',data={'csrf':'test-csrf','id':oid,'course':'DBMS','rating':'4','note':'Updated note','tags':'theory'})
        assert feedback_list()[0][0]['rating']==4
        assert b'Updated note' in client.get('/lab/mongodb').data
        client.post('/lab/mongodb',data={'csrf':'test-csrf','action':'delete','id':oid})
        assert not feedback_list()[0]
    finally:
        with MongoClient(uri) as mongo:
            assert name.startswith('campusweave_test_');mongo.drop_database(name)
