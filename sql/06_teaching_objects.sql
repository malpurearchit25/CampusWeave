-- An updatable single-table view, contrasted with the joined reporting view.
CREATE VIEW active_room_catalog AS SELECT room_id,room_code,room_name,room_type,capacity,is_active FROM rooms WHERE is_active=1 WITH CASCADED CHECK OPTION;
DELIMITER $$
CREATE FUNCTION fn_run_hours(p_run INT) RETURNS INT READS SQL DATA
BEGIN
 DECLARE v_hours INT;
 SELECT COUNT(*) INTO v_hours FROM timetable_entries WHERE run_id=p_run;
 RETURN v_hours;
END$$
DELIMITER ;

-- Expose names/events only; the app does not receive TRIGGER administration.
CREATE PROCEDURE sp_trigger_inventory() SQL SECURITY DEFINER READS SQL DATA SELECT TRIGGER_NAME,EVENT_MANIPULATION,EVENT_OBJECT_TABLE FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE();
