-- Preserve the meaning of saved schedules. Create new catalog records for a new academic edition.
DELIMITER $$
CREATE TRIGGER trg_faculty_history BEFORE UPDATE ON faculty FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_entries te JOIN course_offerings co USING(offering_id) WHERE co.faculty_id=OLD.faculty_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This record is used by a saved timetable. Create a new record or remove its draft first.'; END IF;
END$$
CREATE TRIGGER trg_courses_history BEFORE UPDATE ON courses FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_entries te JOIN course_offerings co USING(offering_id) WHERE co.course_id=OLD.course_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This record is used by a saved timetable. Create a new record or remove its draft first.'; END IF;
END$$
CREATE TRIGGER trg_divisions_history BEFORE UPDATE ON divisions FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_runs WHERE department_id=NEW.department_id AND academic_year=NEW.academic_year AND semester=NEW.semester AND status IN ('PUBLISHED','ARCHIVED')) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cannot move a division into a frozen academic edition.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_entries te JOIN course_offerings co USING(offering_id) WHERE co.division_id=OLD.division_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This record is used by a saved timetable. Create a new record or remove its draft first.'; END IF;
END$$
CREATE TRIGGER trg_rooms_history BEFORE UPDATE ON rooms FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_entries te  WHERE te.room_id=OLD.room_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This record is used by a saved timetable. Create a new record or remove its draft first.'; END IF;
END$$
CREATE TRIGGER trg_course_offerings_history BEFORE UPDATE ON course_offerings FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM divisions d JOIN timetable_runs tr ON tr.department_id=d.department_id AND tr.academic_year=d.academic_year AND tr.semester=d.semester WHERE d.division_id=NEW.division_id AND tr.status IN ('PUBLISHED','ARCHIVED')) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cannot move an offering into a frozen academic edition.'; END IF;
 IF EXISTS(SELECT 1 FROM timetable_entries te  WHERE te.offering_id=OLD.offering_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This record is used by a saved timetable. Create a new record or remove its draft first.'; END IF;
END$$
CREATE TRIGGER trg_offering_scope BEFORE INSERT ON course_offerings FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM divisions d JOIN timetable_runs tr ON tr.department_id=d.department_id AND tr.academic_year=d.academic_year AND tr.semester=d.semester
   WHERE d.division_id=NEW.division_id AND tr.status IN ('PUBLISHED','ARCHIVED')) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This academic edition is frozen by a published or archived timetable.'; END IF;
END$$
CREATE TRIGGER trg_unavailable_insert BEFORE INSERT ON faculty_unavailability FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_entries te JOIN course_offerings co USING(offering_id) JOIN timetable_runs tr USING(run_id)
 WHERE co.faculty_id=NEW.faculty_id AND te.day_of_week=NEW.day_of_week AND te.slot_id=NEW.slot_id AND tr.status='PUBLISHED') THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='This availability change conflicts with a published timetable.'; END IF;
END$$
CREATE TRIGGER trg_unavailable_update BEFORE UPDATE ON faculty_unavailability FOR EACH ROW
BEGIN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Remove and recreate availability blocks so they are revalidated.';
END$$
CREATE TRIGGER trg_division_frozen_insert BEFORE INSERT ON divisions FOR EACH ROW
BEGIN
 IF EXISTS(SELECT 1 FROM timetable_runs WHERE department_id=NEW.department_id AND academic_year=NEW.academic_year AND semester=NEW.semester AND status IN ('PUBLISHED','ARCHIVED')) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Cannot add divisions to a frozen academic edition.'; END IF;
END$$
DELIMITER ;
