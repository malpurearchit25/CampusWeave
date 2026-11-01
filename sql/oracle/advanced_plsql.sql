-- ORACLE ONLY. Run plsql_lab.sql first in a disposable teaching schema.
-- Supplied for syllabus coverage; not executed by the MySQL application.
SET SERVEROUTPUT ON;
CREATE TABLE cw_event_log(event_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 event_kind VARCHAR2(40), affected_rows NUMBER, created_at TIMESTAMP DEFAULT SYSTIMESTAMP);
CREATE TABLE cw_cursor_trace(cursor_kind VARCHAR2(40),observed_value VARCHAR2(100));

CREATE OR REPLACE FUNCTION cw_room_utilization(p_room_id IN NUMBER,p_available_periods IN NUMBER DEFAULT 36)
RETURN NUMBER IS v_count NUMBER;
BEGIN
 IF p_available_periods<=0 THEN RAISE_APPLICATION_ERROR(-20010,'Available periods must be positive'); END IF;
 SELECT COUNT(*) INTO v_count FROM cw_entries e JOIN cw_runs r ON e.run_id=r.run_id
 WHERE e.room_id=p_room_id AND r.status='PUBLISHED';
 RETURN ROUND(100*v_count/p_available_periods,2);
END;
/

CREATE OR REPLACE PROCEDURE cw_cursor_demonstration
IS
 CURSOR room_cursor IS SELECT room_id,room_name,capacity FROM cw_rooms ORDER BY room_id;
 CURSOR eligible_rooms(p_students NUMBER) IS SELECT room_name FROM cw_rooms WHERE capacity>=p_students;
 v_room room_cursor%ROWTYPE;
 v_weak SYS_REFCURSOR;
 TYPE strong_room_cursor IS REF CURSOR RETURN cw_rooms%ROWTYPE;
 v_strong strong_room_cursor;
 v_record cw_rooms%ROWTYPE;
 v_name cw_rooms.room_name%TYPE;
 v_implicit_count NUMBER;
BEGIN
 -- Implicit cursor: SQL%ROWCOUNT, SQL%FOUND, SQL%NOTFOUND, SQL%ISOPEN.
 UPDATE cw_rooms SET capacity=capacity WHERE room_id=1;
 v_implicit_count:=SQL%ROWCOUNT;
 INSERT INTO cw_cursor_trace VALUES('IMPLICIT',TO_CHAR(v_implicit_count));
 DBMS_OUTPUT.PUT_LINE('Implicit rows: '||SQL%ROWCOUNT);
 IF SQL%FOUND THEN DBMS_OUTPUT.PUT_LINE('Implicit cursor found a row'); END IF;
 IF NOT SQL%ISOPEN THEN DBMS_OUTPUT.PUT_LINE('Implicit cursor automatically closed'); END IF;
 -- Explicit cursor: OPEN / FETCH / EXIT / CLOSE and cursor attributes.
 OPEN room_cursor;
 LOOP
   FETCH room_cursor INTO v_room;
   EXIT WHEN room_cursor%NOTFOUND;
   DBMS_OUTPUT.PUT_LINE('Explicit #'||room_cursor%ROWCOUNT||': '||v_room.room_name);
   INSERT INTO cw_cursor_trace VALUES('EXPLICIT',v_room.room_name);
 END LOOP;
 IF room_cursor%ISOPEN THEN CLOSE room_cursor; END IF;
 -- Parameterized cursor FOR loop: automatically opens, fetches and closes.
 FOR item IN eligible_rooms(50) LOOP DBMS_OUTPUT.PUT_LINE('Parameterized: '||item.room_name); INSERT INTO cw_cursor_trace VALUES('PARAMETERIZED FOR LOOP',item.room_name); END LOOP;
 -- Weak reference cursor with dynamic SQL and a bound value.
 OPEN v_weak FOR 'SELECT room_name FROM cw_rooms WHERE capacity>=:minimum' USING 50;
 LOOP FETCH v_weak INTO v_name; EXIT WHEN v_weak%NOTFOUND; DBMS_OUTPUT.PUT_LINE('Weak ref: '||v_name); INSERT INTO cw_cursor_trace VALUES('WEAK REF CURSOR',v_name); END LOOP;
 CLOSE v_weak;
 -- Strong reference cursor: fixed row shape.
 OPEN v_strong FOR SELECT * FROM cw_rooms;
 LOOP FETCH v_strong INTO v_record; EXIT WHEN v_strong%NOTFOUND; DBMS_OUTPUT.PUT_LINE('Strong ref: '||v_record.room_name); INSERT INTO cw_cursor_trace VALUES('STRONG REF CURSOR',v_record.room_name); END LOOP;
 CLOSE v_strong;
EXCEPTION WHEN OTHERS THEN
 IF room_cursor%ISOPEN THEN CLOSE room_cursor; END IF;
 RAISE;
END;
/

-- AFTER row trigger for all three DML events. BEFORE row trigger is in plsql_lab.sql.
CREATE OR REPLACE TRIGGER cw_entry_row_events
AFTER INSERT OR UPDATE OR DELETE ON cw_entries FOR EACH ROW
DECLARE v_event VARCHAR2(40);
BEGIN
 IF INSERTING THEN v_event:='AFTER ROW INSERT'; ELSIF UPDATING THEN v_event:='AFTER ROW UPDATE'; ELSE v_event:='AFTER ROW DELETE'; END IF;
 INSERT INTO cw_event_log(event_kind,affected_rows) VALUES(v_event,1);
END;
/
-- Statement-level trigger executes once, including zero-row statements.
CREATE OR REPLACE TRIGGER cw_entry_statement_event
BEFORE INSERT OR UPDATE OR DELETE ON cw_entries
BEGIN INSERT INTO cw_event_log(event_kind,affected_rows) VALUES('BEFORE STATEMENT',NULL); END;
/
-- Compound trigger shares state across row and statement timing points.
CREATE OR REPLACE TRIGGER cw_entry_compound
FOR INSERT OR UPDATE OR DELETE ON cw_entries
COMPOUND TRIGGER
 v_count PLS_INTEGER:=0;
 BEFORE STATEMENT IS BEGIN v_count:=0; END BEFORE STATEMENT;
 AFTER EACH ROW IS BEGIN v_count:=v_count+1; END AFTER EACH ROW;
 AFTER STATEMENT IS BEGIN INSERT INTO cw_event_log(event_kind,affected_rows) VALUES('AFTER STATEMENT / COMPOUND',v_count); END AFTER STATEMENT;
END;
/
CREATE OR REPLACE VIEW cw_entry_room_view AS
SELECT e.entry_id,e.run_id,r.room_id,r.room_name FROM cw_entries e JOIN cw_rooms r ON e.room_id=r.room_id;
CREATE OR REPLACE TRIGGER cw_room_view_update
INSTEAD OF UPDATE ON cw_entry_room_view FOR EACH ROW
BEGIN
 IF UPDATING('ROOM_NAME') THEN UPDATE cw_rooms SET room_name=:NEW.room_name WHERE room_id=:OLD.room_id;
 ELSE RAISE_APPLICATION_ERROR(-20011,'Only the room name can be changed through this view'); END IF;
END;
/

BEGIN cw_cursor_demonstration; END;
/
SELECT * FROM cw_cursor_trace ORDER BY cursor_kind;
SELECT cw_room_utilization(1,36) utilization_percent FROM dual;
INSERT INTO cw_runs(run_id) VALUES(2);
SAVEPOINT before_trigger_demo;
INSERT INTO cw_entries VALUES(10,2,1,2,2,3,1,50);
UPDATE cw_entries SET students=51 WHERE entry_id=10;
DELETE FROM cw_entries WHERE entry_id=10;
UPDATE cw_entry_room_view SET room_name='Computer Laboratory' WHERE entry_id=1;
SELECT * FROM cw_event_log ORDER BY event_id;
ROLLBACK TO before_trigger_demo;
SELECT name,type,line,text FROM user_errors WHERE name LIKE 'CW_%';

-- Optional schema-event trigger: requires relevant Oracle privileges; install only in a disposable schema.
-- CREATE OR REPLACE TRIGGER cw_schema_ddl_audit AFTER CREATE OR ALTER OR DROP ON SCHEMA
-- BEGIN INSERT INTO cw_event_log(event_kind,affected_rows) VALUES(ORA_SYSEVENT,0); END;
-- /
-- Database LOGON/LOGOFF/STARTUP/SHUTDOWN triggers require administrator privileges and are
-- discussed in the workbook, not installed on a shared database by this project.

-- Explicit updatable cursor (FOR UPDATE / WHERE CURRENT OF).
DECLARE
 CURSOR capacity_cursor IS SELECT room_id,capacity FROM cw_rooms FOR UPDATE OF capacity;
BEGIN
 FOR item IN capacity_cursor LOOP
   UPDATE cw_rooms SET capacity=item.capacity WHERE CURRENT OF capacity_cursor;
   INSERT INTO cw_cursor_trace VALUES('FOR UPDATE CURRENT OF',TO_CHAR(item.room_id));
 END LOOP;
 COMMIT;
END;
/
SELECT * FROM cw_cursor_trace ORDER BY cursor_kind;
