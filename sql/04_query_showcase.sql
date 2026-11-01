-- Run after creating and publishing demo timetables. Read-only showcase.
-- Q1: Join four normalized entities: a division's teaching assignments.
SELECT d.division_name,c.course_code,f.faculty_name,co.sessions_per_week
FROM course_offerings co JOIN divisions d USING(division_id)
JOIN courses c USING(course_id) JOIN faculty f USING(faculty_id);

-- Q2: Aggregate published workload, including zero-load faculty (LEFT JOIN).
SELECT f.faculty_name,COALESCE(w.hours,0) hours,f.max_weekly_hours
FROM faculty f LEFT JOIN (
 SELECT co.faculty_id,COUNT(*) hours FROM timetable_entries te
 JOIN timetable_runs tr USING(run_id) JOIN course_offerings co USING(offering_id)
 WHERE tr.status='PUBLISHED' AND tr.academic_year='2026-27' GROUP BY co.faculty_id
) w USING(faculty_id);

-- Q3: Nested NOT EXISTS: faculty with no course eligibility.
SELECT faculty_code,faculty_name FROM faculty f
WHERE NOT EXISTS(SELECT 1 FROM faculty_courses fc WHERE fc.faculty_id=f.faculty_id);

-- Q4: HAVING: courses with multiple eligible faculty.
SELECT c.course_code,COUNT(*) eligible_faculty FROM faculty_courses fc
JOIN courses c USING(course_id) GROUP BY c.course_id,c.course_code HAVING COUNT(*)>1;

-- Q5: View encapsulates a reusable reporting join.
SELECT * FROM faculty_schedule_view WHERE status='PUBLISHED' ORDER BY faculty_name,day_of_week,start_time;

-- Q6: Window function: rank active rooms by occupied published hours.
WITH usage_hours AS (
 SELECT r.room_code,COUNT(te.entry_id) hours FROM rooms r
 LEFT JOIN (timetable_entries te JOIN timetable_runs tr ON tr.run_id=te.run_id AND tr.status='PUBLISHED')
 ON te.room_id=r.room_id WHERE r.is_active=1 GROUP BY r.room_id,r.room_code
)
SELECT room_code,hours,DENSE_RANK() OVER(ORDER BY hours DESC) usage_rank FROM usage_hours;

-- Q7: Inspect index selection. See scripts/benchmark.py for the controlled comparison.
EXPLAIN SELECT * FROM timetable_entries WHERE run_id=1 AND day_of_week='MONDAY' AND slot_id=1;

-- Q8: Data dictionary metadata.
SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_KEY
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION;
