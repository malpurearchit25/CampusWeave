-- MySQL stored SQL/PSM, not Oracle PL/SQL. The separate Oracle lab is in sql/oracle/.
DELIMITER $$
CREATE PROCEDURE sp_validate_run(IN p_run INT)
BEGIN
 DECLARE v_year VARCHAR(20); DECLARE v_dept INT; DECLARE v_sem INT;
 SELECT academic_year,department_id,semester INTO v_year,v_dept,v_sem FROM timetable_runs WHERE run_id=p_run;
 IF v_year IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Timetable does not exist.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_sessions s WHERE s.run_id=p_run AND NOT EXISTS(SELECT 1 FROM timetable_periods p WHERE p.session_id=s.session_id)) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Incomplete session: no occupied periods.'; END IF;
 IF NOT EXISTS(SELECT 1 FROM timetable_entries WHERE run_id=p_run) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='An empty timetable cannot be published.'; END IF;
 IF EXISTS(SELECT 1 FROM divisions d WHERE d.department_id=v_dept AND d.academic_year=v_year AND d.semester=v_sem
   AND NOT EXISTS(SELECT 1 FROM course_offerings co WHERE co.division_id=d.division_id)) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='A division has no course assignments.'; END IF;
 IF EXISTS(SELECT 1 FROM course_offerings co JOIN divisions d USING(division_id) JOIN courses c USING(course_id)
   LEFT JOIN (SELECT offering_id,COUNT(*) n,COUNT(DISTINCT session_no) sessions FROM timetable_entries WHERE run_id=p_run GROUP BY offering_id) x USING(offering_id)
   WHERE d.department_id=v_dept AND d.academic_year=v_year AND d.semester=v_sem AND
   (COALESCE(x.n,0)<>co.sessions_per_week*c.session_duration_slots OR COALESCE(x.sessions,0)<>co.sessions_per_week)) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Incomplete timetable: required weekly sessions are missing.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_entries te JOIN course_offerings co USING(offering_id) JOIN courses c USING(course_id)
   JOIN divisions d USING(division_id) JOIN rooms r USING(room_id) JOIN time_slots ts USING(slot_id)
   WHERE te.run_id=p_run AND (d.department_id<>v_dept OR d.academic_year<>v_year OR d.semester<>v_sem
   OR te.session_no<1 OR te.session_no>co.sessions_per_week OR ts.slot_type<>'TEACHING' OR r.is_active=0
   OR r.capacity<d.student_count OR (c.required_room_type IS NOT NULL AND c.required_room_type<>r.room_type)
   OR EXISTS(SELECT 1 FROM faculty_unavailability fu WHERE fu.faculty_id=co.faculty_id AND fu.day_of_week=te.day_of_week AND fu.slot_id=te.slot_id))) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Entry violates scope, room suitability or faculty availability.'; END IF;
 IF EXISTS(SELECT te.offering_id,te.session_no FROM timetable_entries te JOIN time_slots ts USING(slot_id)
   JOIN course_offerings co USING(offering_id) JOIN courses c USING(course_id) WHERE te.run_id=p_run
   GROUP BY te.offering_id,te.session_no,c.session_duration_slots
   HAVING COUNT(*)<>c.session_duration_slots OR COUNT(DISTINCT te.day_of_week)<>1 OR COUNT(DISTINCT te.room_id)<>1
   OR TIME_TO_SEC(MAX(ts.end_time))-TIME_TO_SEC(MIN(ts.start_time))<>COUNT(*)*3600) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Session blocks must be complete, consecutive and in one room.'; END IF;
 IF EXISTS(SELECT offering_id,day_of_week FROM timetable_entries WHERE run_id=p_run GROUP BY offering_id,day_of_week HAVING COUNT(DISTINCT session_no)>1) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Spread repeated sessions of a course across different days.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_entries a JOIN course_offerings ca ON a.offering_id=ca.offering_id JOIN time_slots sa ON a.slot_id=sa.slot_id
   JOIN timetable_entries b ON a.day_of_week=b.day_of_week AND a.entry_id<>b.entry_id
   JOIN timetable_runs rb ON b.run_id=rb.run_id JOIN course_offerings cb ON b.offering_id=cb.offering_id JOIN time_slots sb ON b.slot_id=sb.slot_id
   WHERE a.run_id=p_run AND (b.run_id=p_run OR (rb.status='PUBLISHED' AND rb.academic_year=v_year))
   AND sa.start_time<sb.end_time AND sa.end_time>sb.start_time
   AND (a.room_id=b.room_id OR ca.faculty_id=cb.faculty_id OR ca.division_id=cb.division_id)) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Faculty, room or division clash with this or another published timetable.'; END IF;
 IF EXISTS(SELECT co.faculty_id FROM timetable_entries te JOIN timetable_runs tr USING(run_id)
   JOIN course_offerings co USING(offering_id) JOIN faculty f USING(faculty_id)
   WHERE te.run_id=p_run OR (tr.status='PUBLISHED' AND tr.academic_year=v_year AND tr.run_id<>p_run)
   GROUP BY co.faculty_id,f.max_weekly_hours HAVING COUNT(*)>f.max_weekly_hours) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Combined published faculty workload exceeds its weekly limit.'; END IF;
END$$

CREATE PROCEDURE sp_publish_run(IN p_run INT, IN p_actor INT)
BEGIN
 DECLARE v_lock INT; DECLARE v_status VARCHAR(20);
 -- Caller owns COMMIT/ROLLBACK. This procedure must remain part of the caller's atomic transaction.
 SELECT lock_id INTO v_lock FROM scheduling_lock WHERE lock_id=1 FOR UPDATE;
 SELECT status INTO v_status FROM timetable_runs WHERE run_id=p_run FOR UPDATE;
 IF v_status IS NULL OR v_status<>'DRAFT' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Only an existing draft can be published.'; END IF;
 IF NOT EXISTS(SELECT 1 FROM users WHERE user_id=p_actor AND is_active=1 AND role IN ('ADMIN','HOD','COORDINATOR')) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='An active coordinator is required.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_runs r JOIN timetable_runs target ON target.run_id=p_run
   WHERE r.status='PUBLISHED' AND r.department_id=target.department_id AND r.academic_year=target.academic_year AND r.semester=target.semester) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Archive the existing published timetable for this cohort first.'; END IF;
 CALL sp_validate_run(p_run);
 SET @campus_actor=p_actor;
 UPDATE timetable_runs SET status='PUBLISHED' WHERE run_id=p_run;
END$$

CREATE TRIGGER trg_session_insert BEFORE INSERT ON timetable_sessions FOR EACH ROW
BEGIN
 DECLARE v_lock INT;
 SELECT lock_id INTO v_lock FROM scheduling_lock WHERE lock_id=1 FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM course_offerings co JOIN divisions d USING(division_id) JOIN courses c USING(course_id)
   JOIN timetable_runs tr ON tr.run_id=NEW.run_id JOIN rooms r ON r.room_id=NEW.room_id
   WHERE co.offering_id=NEW.offering_id AND tr.status='DRAFT' AND d.department_id=tr.department_id
   AND d.academic_year=tr.academic_year AND d.semester=tr.semester
   AND NEW.session_no BETWEEN 1 AND co.sessions_per_week AND r.is_active=1 AND r.capacity>=d.student_count
   AND (c.required_room_type IS NULL OR c.required_room_type=r.room_type)) THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Invalid entry: check draft scope, session, capacity and required room type.'; END IF;
END$$
CREATE TRIGGER trg_validate_timetable_entry BEFORE INSERT ON timetable_periods FOR EACH ROW
BEGIN
 DECLARE v_lock INT; DECLARE v_run INT; DECLARE v_faculty INT; DECLARE v_division INT;
 DECLARE v_room INT; DECLARE v_day VARCHAR(12);
 SELECT lock_id INTO v_lock FROM scheduling_lock WHERE lock_id=1 FOR UPDATE;
 SELECT s.run_id,co.faculty_id,co.division_id,s.room_id,s.day_of_week
 INTO v_run,v_faculty,v_division,v_room,v_day FROM timetable_sessions s
 JOIN course_offerings co USING(offering_id) WHERE session_id=NEW.session_id;
 IF NOT EXISTS(SELECT 1 FROM timetable_runs WHERE run_id=v_run AND status='DRAFT') THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Entries can only be added to a draft.'; END IF;
 IF NOT EXISTS(SELECT 1 FROM time_slots WHERE slot_id=NEW.slot_id AND slot_type='TEACHING') THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Only teaching periods may be allocated.'; END IF;
 IF EXISTS(SELECT 1 FROM faculty_unavailability WHERE faculty_id=v_faculty AND day_of_week=v_day AND slot_id=NEW.slot_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Faculty is unavailable in this slot.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_entries te JOIN course_offerings co USING(offering_id)
 WHERE te.run_id=v_run AND te.day_of_week=v_day AND te.slot_id=NEW.slot_id
 AND (co.faculty_id=v_faculty OR co.division_id=v_division OR te.room_id=v_room)) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Resource clash: faculty, room or division already occupied.'; END IF;
END$$
CREATE TRIGGER trg_entry_immutable BEFORE UPDATE ON timetable_periods FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Scheduled entries are immutable. Delete the draft and generate a new version.'; END$$
CREATE TRIGGER trg_session_immutable BEFORE UPDATE ON timetable_sessions FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Saved session headers are immutable. Generate a new draft.'; END$$
CREATE TRIGGER trg_entry_delete BEFORE DELETE ON timetable_periods FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_sessions s JOIN timetable_runs tr USING(run_id) WHERE s.session_id=OLD.session_id AND tr.status<>'DRAFT') THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Published and archived entries are retained for audit.'; END IF;
END$$
CREATE TRIGGER trg_session_delete BEFORE DELETE ON timetable_sessions FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_runs WHERE run_id=OLD.run_id AND status<>'DRAFT') THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Published and archived sessions are retained for audit.'; END IF;
END$$
CREATE TRIGGER trg_run_transition BEFORE UPDATE ON timetable_runs FOR EACH ROW
BEGIN
 DECLARE v_lock INT;
 SELECT lock_id INTO v_lock FROM scheduling_lock WHERE lock_id=1 FOR UPDATE;
 IF NOT ((OLD.status='DRAFT' AND NEW.status='PUBLISHED') OR (OLD.status='PUBLISHED' AND NEW.status='ARCHIVED')) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Allowed transitions: draft to published; published to archived.'; END IF;
 IF NEW.department_id<>OLD.department_id OR NEW.academic_year<>OLD.academic_year OR NEW.semester<>OLD.semester OR NEW.created_by<>OLD.created_by THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Run identity is immutable.'; END IF;
 IF NEW.status='PUBLISHED' THEN
   IF EXISTS(SELECT 1 FROM timetable_runs WHERE status='PUBLISHED' AND department_id=OLD.department_id
     AND academic_year=OLD.academic_year AND semester=OLD.semester AND run_id<>OLD.run_id) THEN
     SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Only one timetable per cohort can be published.'; END IF;
   CALL sp_validate_run(OLD.run_id);
 END IF;
END$$
CREATE TRIGGER trg_run_audit AFTER UPDATE ON timetable_runs FOR EACH ROW
BEGIN
 INSERT INTO approval_history(run_id,action_by,action,comments)
 VALUES(NEW.run_id,COALESCE(@campus_actor,NEW.created_by),NEW.status,'Recorded automatically by database trigger');
END$$
CREATE TRIGGER trg_slot_insert BEFORE INSERT ON time_slots FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM time_slots WHERE NEW.start_time<end_time AND NEW.end_time>start_time) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Time slots must not overlap.'; END IF;
END$$
CREATE TRIGGER trg_slot_update BEFORE UPDATE ON time_slots FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_entries WHERE slot_id=OLD.slot_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='A used slot is immutable.'; END IF;
 IF EXISTS(SELECT 1 FROM time_slots WHERE slot_id<>OLD.slot_id AND NEW.start_time<end_time AND NEW.end_time>start_time) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Time slots must not overlap.'; END IF;
END$$
DELIMITER ;
