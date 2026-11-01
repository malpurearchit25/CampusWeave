from concurrent.futures import ThreadPoolExecutor
import pytest
import mysql.connector
from db import query,transaction,execute,call,rows
from scheduler import generate

def add_entry(cn,run,offering,number,room,day,slot):
    found=rows(cn,'SELECT session_id FROM timetable_sessions WHERE run_id=%s AND offering_id=%s AND session_no=%s',(run,offering,number))
    session=found[0]['session_id'] if found else execute(cn,'INSERT INTO timetable_sessions(run_id,offering_id,session_no,room_id,day_of_week) VALUES(%s,%s,%s,%s,%s)',(run,offering,number,room,day))
    return execute(cn,'INSERT INTO timetable_periods(session_id,slot_id) VALUES(%s,%s)',(session,slot))

def draft():return generate(1,'2026-27',3,1)[0]
def publish(run):
    with transaction() as cn:call(cn,'sp_publish_run',(run,1))
def archive(run):
    with transaction() as cn:execute(cn,"UPDATE timetable_runs SET status='ARCHIVED' WHERE run_id=%s",(run,))

def test_complete_seed_generation():
    run,stats=generate(1,'2026-27',3,1)
    assert stats['sessions']==28
    assert query('SELECT COUNT(*) n FROM timetable_entries WHERE run_id=%s',(run,))[0]['n']==32
    with transaction() as cn:call(cn,'sp_validate_run',(run,))

def test_atomic_publish_and_audit():
    run=draft();publish(run)
    assert query('SELECT status FROM timetable_runs WHERE run_id=%s',(run,))[0]['status']=='PUBLISHED'
    assert query('SELECT action FROM approval_history WHERE run_id=%s',(run,))==[{'action':'PUBLISHED'}]

def test_empty_run_rejected():
    with transaction() as cn:run=execute(cn,"INSERT INTO timetable_runs(department_id,academic_year,semester,created_by) VALUES(1,'2026-27',3,1)")
    with pytest.raises(mysql.connector.Error,match='empty'):publish(run)

def test_missing_session_rejected():
    run=draft()
    with transaction() as cn:execute(cn,'DELETE FROM timetable_periods LIMIT 1')
    with pytest.raises(mysql.connector.Error,match='Incomplete'):publish(run)

def test_insert_trigger_rejects_resource_clash():
    run=draft();e=query('SELECT * FROM timetable_entries WHERE run_id=%s LIMIT 1',(run,))[0]
    with pytest.raises(mysql.connector.Error,match='clash'):
        with transaction() as cn:add_entry(cn,run,e['offering_id'],e['session_no'],e['room_id'],e['day_of_week'],e['slot_id'])

def test_wrong_lab_type_rejected():
    with transaction() as cn:run=execute(cn,"INSERT INTO timetable_runs(department_id,academic_year,semester,created_by) VALUES(1,'2026-27',3,1)")
    with pytest.raises(mysql.connector.Error,match='Invalid entry'):
        with transaction() as cn:add_entry(cn,run,3,1,7,'MONDAY',1)

def test_unavailable_period_rejected():
    with transaction() as cn:run=execute(cn,"INSERT INTO timetable_runs(department_id,academic_year,semester,created_by) VALUES(1,'2026-27',3,1)")
    with pytest.raises(mysql.connector.Error,match='unavailable'):
        with transaction() as cn:add_entry(cn,run,1,1,1,'MONDAY',2)

def test_update_bypass_is_blocked():
    run=draft()
    with pytest.raises(mysql.connector.Error,match='immutable'):
        with transaction() as cn:execute(cn,'UPDATE timetable_periods SET slot_id=2 LIMIT 1')

def test_failed_multiwrite_rolls_back_everything():
    before=query('SELECT COUNT(*) n FROM timetable_runs')[0]['n']
    with pytest.raises(mysql.connector.Error):
        with transaction() as cn:
            run=execute(cn,"INSERT INTO timetable_runs(department_id,academic_year,semester,created_by) VALUES(1,'2026-27',3,1)")
            add_entry(cn,run,1,1,1,'MONDAY',1)
            add_entry(cn,run,1,1,1,'MONDAY',1)
    assert query('SELECT COUNT(*) n FROM timetable_runs')[0]['n']==before
    assert query('SELECT COUNT(*) n FROM timetable_entries')[0]['n']==0
    assert query('SELECT COUNT(*) n FROM timetable_sessions')[0]['n']==0

def test_saved_catalog_is_immutable():
    draft()
    with pytest.raises(mysql.connector.Error,match='saved timetable'):
        with transaction() as cn:execute(cn,"UPDATE faculty SET faculty_name='Changed' WHERE faculty_id=1")

def test_cross_semester_resources_and_workload():
    first=draft();publish(first);second=generate(1,'2026-27',5,1)[0];publish(second)
    assert query("SELECT COUNT(*) n FROM timetable_runs WHERE status='PUBLISHED'")[0]['n']==2
    with transaction() as cn:call(cn,'sp_validate_run',(second,))

def test_concurrent_publication_only_one_wins():
    a,b=draft(),draft()
    def attempt(run):
        try:publish(run);return True
        except mysql.connector.Error:return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,[a,b]))
    assert sorted(results)==[False,True]
    assert query('SELECT COUNT(*) n FROM approval_history')[0]['n']==1

def test_archiving_preserves_history_and_releases_scope():
    run=draft();publish(run);archive(run)
    assert query('SELECT COUNT(*) n FROM timetable_entries WHERE run_id=%s',(run,))[0]['n']==32
    replacement=draft();publish(replacement)
    assert [r['action'] for r in query('SELECT action FROM approval_history WHERE run_id=%s ORDER BY approval_id',(run,))]==['PUBLISHED','ARCHIVED']

def test_published_delete_is_rejected():
    run=draft();publish(run)
    with pytest.raises(mysql.connector.Error,match='retained'):
        with transaction() as cn:execute(cn,'DELETE FROM timetable_periods LIMIT 1')

def test_impossible_workload_creates_no_draft():
    with transaction() as cn:execute(cn,'UPDATE faculty SET max_weekly_hours=1 WHERE faculty_id=1')
    with pytest.raises(ValueError,match='workload'):draft()
    assert query('SELECT COUNT(*) n FROM timetable_runs')[0]['n']==0

def test_overlapping_time_slots_rejected():
    with pytest.raises(mysql.connector.Error,match='overlap'):
        with transaction() as cn:execute(cn,"INSERT INTO time_slots(start_time,end_time) VALUES('09:30','10:30')")

def test_practicals_do_not_cross_lunch():
    run=draft()
    blocks=query('''SELECT te.offering_id,te.session_no,MIN(ts.start_time) start,MAX(ts.end_time) end,COUNT(*) n
        FROM timetable_entries te JOIN course_offerings co USING(offering_id) JOIN courses c USING(course_id)
        JOIN time_slots ts USING(slot_id) WHERE run_id=%s AND c.subject_type='PRACTICAL' GROUP BY te.offering_id,te.session_no''',(run,))
    assert len(blocks)==4
    assert all((b['end']-b['start']).total_seconds()==7200 and b['n']==2 for b in blocks)

def test_eligibility_foreign_key():
    with pytest.raises(mysql.connector.Error):
        with transaction() as cn:execute(cn,'INSERT INTO course_offerings(division_id,course_id,faculty_id,sessions_per_week) VALUES(3,1,4,2)')

def test_session_headers_are_normalized_and_immutable():
    run=draft()
    assert query('SELECT COUNT(*) n FROM timetable_sessions WHERE run_id=%s',(run,))[0]['n']==28
    columns={r['COLUMN_NAME'] for r in query("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='timetable_periods'")}
    assert columns=={'entry_id','session_id','slot_id'}
    with pytest.raises(mysql.connector.Error,match='immutable'):
        with transaction() as cn:execute(cn,'UPDATE timetable_sessions SET room_id=1 WHERE run_id=%s LIMIT 1',(run,))

def test_division_cannot_be_added_to_published_edition():
    run=draft();publish(run)
    with pytest.raises(mysql.connector.Error,match='frozen'):
        with transaction() as cn:execute(cn,"INSERT INTO divisions(division_name,department_id,academic_year,semester,student_count) VALUES('SE-C',1,'2026-27',3,60)")
