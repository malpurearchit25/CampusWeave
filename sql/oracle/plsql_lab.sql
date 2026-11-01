-- OPTIONAL ORACLE PL/SQL DIALECT LAB. Run in a fresh Oracle schema, NOT MySQL.
-- This compact companion demonstrates PL/SQL syntax with timetable-domain data.
-- It is not a claim that the full Flask application runs on Oracle.
SET SERVEROUTPUT ON;
CREATE TABLE cw_rooms(room_id NUMBER PRIMARY KEY, room_name VARCHAR2(40), capacity NUMBER CHECK(capacity>0));
CREATE TABLE cw_runs(run_id NUMBER PRIMARY KEY, status VARCHAR2(12) DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','PUBLISHED')));
CREATE TABLE cw_entries(entry_id NUMBER PRIMARY KEY, run_id NUMBER REFERENCES cw_runs(run_id),
 room_id NUMBER REFERENCES cw_rooms(room_id), faculty_id NUMBER NOT NULL, division_id NUMBER NOT NULL,
 day_no NUMBER CHECK(day_no BETWEEN 1 AND 6), slot_no NUMBER CHECK(slot_no BETWEEN 1 AND 6), students NUMBER CHECK(students>0));
CREATE TABLE cw_audit(audit_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,run_id NUMBER REFERENCES cw_runs(run_id),
 old_status VARCHAR2(12),new_status VARCHAR2(12),changed_at TIMESTAMP DEFAULT SYSTIMESTAMP);

CREATE OR REPLACE TRIGGER cw_capacity_guard
BEFORE INSERT OR UPDATE ON cw_entries FOR EACH ROW
DECLARE v_capacity NUMBER; v_status VARCHAR2(12);
BEGIN
 SELECT capacity INTO v_capacity FROM cw_rooms WHERE room_id=:NEW.room_id;
 SELECT status INTO v_status FROM cw_runs WHERE run_id=:NEW.run_id;
 IF :NEW.students>v_capacity THEN RAISE_APPLICATION_ERROR(-20001,'Room capacity exceeded'); END IF;
 IF v_status<>'DRAFT' THEN RAISE_APPLICATION_ERROR(-20002,'Only draft entries can be changed'); END IF;
END;
/
CREATE OR REPLACE TRIGGER cw_publication_audit
AFTER UPDATE OF status ON cw_runs FOR EACH ROW
BEGIN
 INSERT INTO cw_audit(run_id,old_status,new_status) VALUES(:NEW.run_id,:OLD.status,:NEW.status);
END;
/
CREATE OR REPLACE PROCEDURE cw_publish_run(p_run_id IN NUMBER)
IS v_status VARCHAR2(12);v_count NUMBER;
BEGIN
 SELECT status INTO v_status FROM cw_runs WHERE run_id=p_run_id FOR UPDATE;
 IF v_status<>'DRAFT' THEN RAISE_APPLICATION_ERROR(-20003,'Only drafts can be published'); END IF;
 SELECT COUNT(*) INTO v_count FROM cw_entries WHERE run_id=p_run_id;
 IF v_count=0 THEN RAISE_APPLICATION_ERROR(-20004,'Empty run'); END IF;
 SELECT COUNT(*) INTO v_count FROM cw_entries a JOIN cw_entries b ON a.run_id=b.run_id
 AND a.entry_id<b.entry_id AND a.day_no=b.day_no AND a.slot_no=b.slot_no
 WHERE a.run_id=p_run_id AND (a.room_id=b.room_id OR a.faculty_id=b.faculty_id OR a.division_id=b.division_id);
 IF v_count>0 THEN RAISE_APPLICATION_ERROR(-20005,'Resource clash'); END IF;
 UPDATE cw_runs SET status='PUBLISHED' WHERE run_id=p_run_id;
 DBMS_OUTPUT.PUT_LINE('Published run '||p_run_id||'; caller must COMMIT or ROLLBACK.');
EXCEPTION WHEN NO_DATA_FOUND THEN RAISE_APPLICATION_ERROR(-20006,'Run not found');
END;
/
INSERT INTO cw_rooms VALUES(1,'Computer Lab',60);
INSERT INTO cw_runs(run_id) VALUES(1);
INSERT INTO cw_entries VALUES(1,1,1,1,1,1,1,55);
COMMIT;
BEGIN
 SAVEPOINT before_publication;
 cw_publish_run(1);
 ROLLBACK TO before_publication;
 DBMS_OUTPUT.PUT_LINE('Publication and audit rolled back together.');
END;
/
SELECT * FROM cw_runs;
SELECT * FROM cw_audit;
-- Expected: DRAFT and no audit rows after rollback.
BEGIN
 INSERT INTO cw_entries VALUES(2,1,1,2,2,2,1,90);
EXCEPTION WHEN OTHERS THEN
 IF SQLCODE=-20001 THEN DBMS_OUTPUT.PUT_LINE('Expected capacity rejection: '||SQLERRM); ELSE RAISE; END IF;
END;
/
BEGIN cw_publish_run(1); END;
/
COMMIT;
SELECT * FROM cw_audit;
-- Expected: one publication record. Verify compilation with USER_ERRORS.
SELECT name,type,line,text FROM user_errors WHERE name LIKE 'CW_%';
