-- Execute in the isolated course-lab database created by scripts/sql_experiments.py.
-- 1. DDL and DML: constraints, insert, update, delete, alter and rollback.
CREATE TABLE lab_resources(id INT PRIMARY KEY,code VARCHAR(20) UNIQUE,capacity INT CHECK(capacity>0),note VARCHAR(100));
INSERT INTO lab_resources VALUES(1,'A',60,NULL),(2,'B',90,'Large room');
ALTER TABLE lab_resources ADD reviewed BOOLEAN NOT NULL DEFAULT FALSE;
START TRANSACTION;
UPDATE lab_resources SET reviewed=TRUE WHERE capacity>=60;
SAVEPOINT after_review;
DELETE FROM lab_resources WHERE id=2;
ROLLBACK TO SAVEPOINT after_review;
ROLLBACK;

-- 2. Conditional/logical operators, LIKE, NOT LIKE, IN, NOT IN, BETWEEN, NULL.
SELECT * FROM rooms WHERE capacity BETWEEN 55 AND 90 AND is_active=1 AND room_code LIKE 'A%';
SELECT * FROM courses WHERE subject_type IN ('THEORY','TUTORIAL') AND course_code NOT LIKE '%LAB%';
SELECT * FROM rooms WHERE room_type NOT IN ('CLASSROOM') OR capacity>80;
SELECT * FROM faculty WHERE user_id IS NULL;
SELECT * FROM lab_resources WHERE note IS NOT NULL;

-- 3. Single-row string/date/time/numeric functions.
SELECT UPPER(course_code),CONCAT(course_code,' - ',course_name),CHAR_LENGTH(course_name) FROM courses;
SELECT CURRENT_DATE(),YEAR(CURRENT_DATE()),DATE_ADD(CURRENT_DATE(),INTERVAL 7 DAY),TIME_FORMAT(start_time,'%H:%i') FROM time_slots LIMIT 1;
SELECT faculty_name,ROUND(max_weekly_hours/6,2) daily_average,CEIL(max_weekly_hours/6) upper_daily FROM faculty;

-- 4. Aggregation, ORDER BY, GROUP BY and HAVING.
SELECT subject_type,COUNT(*) subjects,SUM(sessions_per_week) sessions,AVG(session_duration_slots) duration
FROM courses GROUP BY subject_type HAVING COUNT(*)>=1 ORDER BY subjects DESC;

-- 5. Set operators: compatible projections, duplicate elimination/retention.
SELECT faculty_id FROM faculty_courses WHERE course_id=1 UNION SELECT faculty_id FROM faculty_courses WHERE course_id=2;
SELECT faculty_id FROM faculty_courses WHERE course_id=1 UNION ALL SELECT faculty_id FROM faculty_courses WHERE course_id=2;
SELECT faculty_id FROM faculty_courses WHERE course_id=1 INTERSECT SELECT faculty_id FROM faculty_courses WHERE course_id=5;
SELECT faculty_id FROM faculty EXCEPT SELECT faculty_id FROM faculty_courses WHERE course_id=1;

-- 6. Equijoin, non-equijoin, self join and outer join.
SELECT f.faculty_name,d.department_name FROM faculty f JOIN departments d ON f.department_id=d.department_id;
SELECT d.division_name,r.room_code FROM divisions d JOIN rooms r ON r.capacity>=d.student_count;
SELECT a.faculty_name,b.faculty_name FROM faculty a JOIN faculty b ON a.department_id=b.department_id AND a.faculty_id<b.faculty_id;
SELECT d.department_name,f.faculty_name FROM departments d LEFT JOIN faculty f USING(department_id);

-- 7. Scalar, multirow and correlated subqueries, ANY/ALL/EXISTS.
SELECT * FROM rooms WHERE capacity=(SELECT MAX(capacity) FROM rooms);
SELECT * FROM faculty WHERE faculty_id IN (SELECT faculty_id FROM faculty_courses WHERE course_id=1);
SELECT * FROM rooms WHERE capacity>=ALL(SELECT student_count FROM divisions);
SELECT * FROM rooms WHERE capacity>=ANY(SELECT student_count FROM divisions);
SELECT * FROM courses c WHERE EXISTS(SELECT 1 FROM faculty_courses fc WHERE fc.course_id=c.course_id);
SELECT * FROM faculty f WHERE NOT EXISTS(SELECT 1 FROM course_offerings co WHERE co.faculty_id=f.faculty_id);

-- 8. DML containing a subquery, rolled back after inspection.
START TRANSACTION;
UPDATE lab_resources SET reviewed=TRUE WHERE capacity>=(SELECT MIN(student_count) FROM divisions);
SELECT * FROM lab_resources;
ROLLBACK;

-- 9. Updatable view and CHECK OPTION; joined view is used for reading only.
CREATE VIEW lab_room_view AS SELECT id,code,capacity FROM lab_resources WHERE capacity>=50 WITH CHECK OPTION;
START TRANSACTION;
UPDATE lab_room_view SET capacity=70 WHERE id=1;
SELECT * FROM lab_resources WHERE id=1;
ROLLBACK;
SELECT * FROM faculty_schedule_view LIMIT 3;

-- 10. Dynamic SQL: identifiers are fixed by code; values remain bound.
SET @statement='SELECT course_code,course_name FROM courses WHERE subject_type=?';
PREPARE course_query FROM @statement;
SET @course_type='PRACTICAL';
EXECUTE course_query USING @course_type;
DEALLOCATE PREPARE course_query;

-- 11. Function and metadata.
SELECT fn_run_hours(999999) empty_run_hours;
SELECT TABLE_NAME,IS_UPDATABLE FROM information_schema.VIEWS WHERE TABLE_SCHEMA=DATABASE();
SELECT CONSTRAINT_NAME,CONSTRAINT_TYPE FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE();
