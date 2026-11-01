from db import transaction,execute,rows,lock_catalog

def load_mart():
    with transaction() as cn:
        lock_catalog(cn)
        execute(cn,'INSERT IGNORE INTO dw_subject SELECT course_id,course_code,course_name,subject_type FROM courses')
        execute(cn,'INSERT IGNORE INTO dw_faculty SELECT faculty_id,faculty_name,department_name FROM faculty JOIN departments USING(department_id)')
        execute(cn,'INSERT IGNORE INTO dw_cohort SELECT division_id,division_name,department_name,academic_year,semester FROM divisions JOIN departments USING(department_id)')
        execute(cn,'INSERT IGNORE INTO dw_period SELECT slot_id,start_time,end_time,slot_type FROM time_slots')
        execute(cn,'''INSERT IGNORE INTO dw_teaching_fact(source_entry_id,run_id,subject_key,faculty_key,cohort_key,period_key,day_of_week,teaching_hours)
          SELECT te.entry_id,te.run_id,co.course_id,co.faculty_id,co.division_id,te.slot_id,te.day_of_week,1
          FROM timetable_entries te JOIN course_offerings co USING(offering_id) JOIN timetable_runs tr USING(run_id) WHERE tr.status='PUBLISHED' ''')
        return rows(cn,'SELECT COUNT(*) n FROM dw_teaching_fact')[0]['n']

def olap():
    with transaction() as cn:
        return rows(cn,'''SELECT c.academic_year,c.semester,s.subject_type,SUM(f.teaching_hours) hours
          FROM dw_teaching_fact f JOIN dw_cohort c ON f.cohort_key=c.cohort_key JOIN dw_subject s ON f.subject_key=s.subject_key
          GROUP BY c.academic_year,c.semester,s.subject_type WITH ROLLUP''')
