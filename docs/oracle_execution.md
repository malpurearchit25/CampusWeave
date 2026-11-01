# Oracle 21c execution evidence

https://dbfiddle.uk/x6YRxBnX

```sql
CREATE TABLE cw_rooms(room_id NUMBER PRIMARY KEY, room_name VARCHAR2(40), capacity NUMBER CHECK(capacity>0));
```
```sql
CREATE TABLE cw_runs(run_id NUMBER PRIMARY KEY, status VARCHAR2(12) DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','PUBLISHED')));
```
```sql
CREATE TABLE cw_entries(entry_id NUMBER PRIMARY KEY, run_id NUMBER REFERENCES cw_runs(run_id),
 room_id NUMBER REFERENCES cw_rooms(room_id), faculty_id NUMBER NOT NULL, division_id NUMBER NOT NULL,
 day_no NUMBER CHECK(day_no BETWEEN 1 AND 6), slot_no NUMBER CHECK(slot_no BETWEEN 1 AND 6), students NUMBER CHECK(students>0));
```
```sql
CREATE TABLE cw_audit(audit_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,run_id NUMBER REFERENCES cw_runs(run_id),
 old_status VARCHAR2(12),new_status VARCHAR2(12),changed_at TIMESTAMP DEFAULT SYSTIMESTAMP);
```
```sql
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
```
```sql
CREATE OR REPLACE TRIGGER cw_publication_audit
AFTER UPDATE OF status ON cw_runs FOR EACH ROW
BEGIN
 INSERT INTO cw_audit(run_id,old_status,new_status) VALUES(:NEW.run_id,:OLD.status,:NEW.status);
END;
/
```
```sql
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
```
```sql
INSERT INTO cw_rooms VALUES(1,'Computer Lab',60);
```
> ``` status
> 1 rows affected
> ```

```sql
INSERT INTO cw_runs(run_id) VALUES(1);
```
> ``` status
> 1 rows affected
> ```

```sql
INSERT INTO cw_entries VALUES(1,1,1,1,1,1,1,55);
```
> ``` status
> 1 rows affected
> ```

```sql
COMMIT;
```
```sql
BEGIN
 SAVEPOINT before_publication;
 cw_publish_run(1);
 ROLLBACK TO before_publication;
 DBMS_OUTPUT.PUT_LINE('Publication and audit rolled back together.');
END;
/
```
> ``` status
> 1 rows affected
> ```

> ``` dbms_output
> Published run 1; caller must COMMIT or ROLLBACK.
> Publication and audit rolled back together.
> ```

```sql
SELECT * FROM cw_runs;
```
| RUN\_ID | STATUS |
|-------:|:-------|
| 1 | DRAFT |

```sql
SELECT * FROM cw_audit;
```
| AUDIT\_ID | RUN\_ID | OLD\_STATUS | NEW\_STATUS | CHANGED\_AT |
|---------:|-------:|:-----------|:-----------|:-----------|

```sql
BEGIN
 INSERT INTO cw_entries VALUES(2,1,1,2,2,2,1,90);
EXCEPTION WHEN OTHERS THEN
 IF SQLCODE=-20001 THEN DBMS_OUTPUT.PUT_LINE('Expected capacity rejection: '||SQLERRM); ELSE RAISE; END IF;
END;
/
```
> ``` status
> 1 rows affected
> ```

> ``` dbms_output
> Expected capacity rejection: ORA-20001: Room capacity exceeded
> ORA-06512: at "FIDDLE.CW_CAPACITY_GUARD", line 5
> ORA-04088: error during execution of trigger 'FIDDLE.CW_CAPACITY_GUARD'
> ```

```sql
BEGIN cw_publish_run(1); END;
/
```
> ``` status
> 1 rows affected
> ```

```sql
COMMIT;
```
```sql
SELECT * FROM cw_audit;
```
| AUDIT\_ID | RUN\_ID | OLD\_STATUS | NEW\_STATUS | CHANGED\_AT |
|---------:|-------:|:-----------|:-----------|:-----------|
| 2 | 1 | DRAFT | PUBLISHED | 31-OCT-26 07.50.39.886963 PM |

```sql
SELECT name,type,line,text FROM user_errors WHERE name LIKE 'CW_%';
```
| NAME | TYPE | LINE | TEXT |
|:-----|:-----|-----:|:-----|

```sql
CREATE TABLE cw_event_log(event_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 event_kind VARCHAR2(40), affected_rows NUMBER, created_at TIMESTAMP DEFAULT SYSTIMESTAMP);
```
```sql
CREATE TABLE cw_cursor_trace(cursor_kind VARCHAR2(40),observed_value VARCHAR2(100));
```
```sql
CREATE OR REPLACE FUNCTION cw_room_utilization(p_room_id IN NUMBER,p_available_periods IN NUMBER DEFAULT 36)
RETURN NUMBER IS v_count NUMBER;
BEGIN
 IF p_available_periods<=0 THEN RAISE_APPLICATION_ERROR(-20010,'Available periods must be positive'); END IF;
 SELECT COUNT(*) INTO v_count FROM cw_entries e JOIN cw_runs r ON e.run_id=r.run_id
 WHERE e.room_id=p_room_id AND r.status='PUBLISHED';
 RETURN ROUND(100*v_count/p_available_periods,2);
END;
/
```
```sql
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
 UPDATE cw_rooms SET capacity=capacity WHERE room_id=1;
 v_implicit_count:=SQL%ROWCOUNT;
 INSERT INTO cw_cursor_trace VALUES('IMPLICIT',TO_CHAR(v_implicit_count));
 DBMS_OUTPUT.PUT_LINE('Implicit rows: '||SQL%ROWCOUNT);
 IF SQL%FOUND THEN DBMS_OUTPUT.PUT_LINE('Implicit cursor found a row'); END IF;
 IF NOT SQL%ISOPEN THEN DBMS_OUTPUT.PUT_LINE('Implicit cursor automatically closed'); END IF;
 OPEN room_cursor;
 LOOP
   FETCH room_cursor INTO v_room;
   EXIT WHEN room_cursor%NOTFOUND;
   DBMS_OUTPUT.PUT_LINE('Explicit #'||room_cursor%ROWCOUNT||': '||v_room.room_name);
   INSERT INTO cw_cursor_trace VALUES('EXPLICIT',v_room.room_name);
 END LOOP;
 IF room_cursor%ISOPEN THEN CLOSE room_cursor; END IF;
 FOR item IN eligible_rooms(50) LOOP DBMS_OUTPUT.PUT_LINE('Parameterized: '||item.room_name); INSERT INTO cw_cursor_trace VALUES('PARAMETERIZED FOR LOOP',item.room_name); END LOOP;
 OPEN v_weak FOR 'SELECT room_name FROM cw_rooms WHERE capacity>=:minimum' USING 50;
 LOOP FETCH v_weak INTO v_name; EXIT WHEN v_weak%NOTFOUND; DBMS_OUTPUT.PUT_LINE('Weak ref: '||v_name); INSERT INTO cw_cursor_trace VALUES('WEAK REF CURSOR',v_name); END LOOP;
 CLOSE v_weak;
 OPEN v_strong FOR SELECT * FROM cw_rooms;
 LOOP FETCH v_strong INTO v_record; EXIT WHEN v_strong%NOTFOUND; DBMS_OUTPUT.PUT_LINE('Strong ref: '||v_record.room_name); INSERT INTO cw_cursor_trace VALUES('STRONG REF CURSOR',v_record.room_name); END LOOP;
 CLOSE v_strong;
EXCEPTION WHEN OTHERS THEN
 IF room_cursor%ISOPEN THEN CLOSE room_cursor; END IF;
 RAISE;
END;
/
```
```sql
CREATE OR REPLACE TRIGGER cw_entry_row_events
AFTER INSERT OR UPDATE OR DELETE ON cw_entries FOR EACH ROW
DECLARE v_event VARCHAR2(40);
BEGIN
 IF INSERTING THEN v_event:='AFTER ROW INSERT'; ELSIF UPDATING THEN v_event:='AFTER ROW UPDATE'; ELSE v_event:='AFTER ROW DELETE'; END IF;
 INSERT INTO cw_event_log(event_kind,affected_rows) VALUES(v_event,1);
END;
/
```
```sql
CREATE OR REPLACE TRIGGER cw_entry_statement_event
BEFORE INSERT OR UPDATE OR DELETE ON cw_entries
BEGIN INSERT INTO cw_event_log(event_kind,affected_rows) VALUES('BEFORE STATEMENT',NULL); END;
/
```
```sql
CREATE OR REPLACE TRIGGER cw_entry_compound
FOR INSERT OR UPDATE OR DELETE ON cw_entries
COMPOUND TRIGGER
 v_count PLS_INTEGER:=0;
 BEFORE STATEMENT IS BEGIN v_count:=0; END BEFORE STATEMENT;
 AFTER EACH ROW IS BEGIN v_count:=v_count+1; END AFTER EACH ROW;
 AFTER STATEMENT IS BEGIN INSERT INTO cw_event_log(event_kind,affected_rows) VALUES('AFTER STATEMENT / COMPOUND',v_count); END AFTER STATEMENT;
END;
/
```
```sql
CREATE OR REPLACE VIEW cw_entry_room_view AS
SELECT e.entry_id,e.run_id,r.room_id,r.room_name FROM cw_entries e JOIN cw_rooms r ON e.room_id=r.room_id;
```
```sql
CREATE OR REPLACE TRIGGER cw_room_view_update
INSTEAD OF UPDATE ON cw_entry_room_view FOR EACH ROW
BEGIN
 IF UPDATING('ROOM_NAME') THEN UPDATE cw_rooms SET room_name=:NEW.room_name WHERE room_id=:OLD.room_id;
 ELSE RAISE_APPLICATION_ERROR(-20011,'Only the room name can be changed through this view'); END IF;
END;
/
```
```sql
BEGIN cw_cursor_demonstration; END;
/
```
> ``` status
> 1 rows affected
> ```

```sql
SELECT * FROM cw_cursor_trace ORDER BY cursor_kind;
```
| CURSOR\_KIND | OBSERVED\_VALUE |
|:------------|:---------------|
| EXPLICIT | Computer Lab |
| IMPLICIT | 1 |
| PARAMETERIZED FOR LOOP | Computer Lab |
| STRONG REF CURSOR | Computer Lab |
| WEAK REF CURSOR | Computer Lab |

```sql
SELECT cw_room_utilization(1,36) utilization_percent FROM dual;
```
| UTILIZATION\_PERCENT |
|--------------------:|
| 2.78 |

```sql
INSERT INTO cw_runs(run_id) VALUES(2);
```
> ``` status
> 1 rows affected
> ```

```sql
SAVEPOINT before_trigger_demo;
```
```sql
INSERT INTO cw_entries VALUES(10,2,1,2,2,3,1,50);
```
> ``` status
> 1 rows affected
> ```

```sql
UPDATE cw_entries SET students=51 WHERE entry_id=10;
```
> ``` status
> 1 rows affected
> ```

```sql
DELETE FROM cw_entries WHERE entry_id=10;
```
> ``` status
> 1 rows affected
> ```

```sql
UPDATE cw_entry_room_view SET room_name='Computer Laboratory' WHERE entry_id=1;
```
> ``` status
> 1 rows affected
> ```

```sql
SELECT * FROM cw_event_log ORDER BY event_id;
```
| EVENT\_ID | EVENT\_KIND | AFFECTED\_ROWS | CREATED\_AT |
|---------:|:-----------|--------------:|:-----------|
| 1 | BEFORE STATEMENT | *null* | 31-OCT-26 07.50.40.406262 PM |
| 2 | AFTER ROW INSERT | 1 | 31-OCT-26 07.50.40.418138 PM |
| 3 | AFTER STATEMENT \/ COMPOUND | 1 | 31-OCT-26 07.50.40.419341 PM |
| 4 | BEFORE STATEMENT | *null* | 31-OCT-26 07.50.40.428971 PM |
| 5 | AFTER ROW UPDATE | 1 | 31-OCT-26 07.50.40.429266 PM |
| 6 | AFTER STATEMENT \/ COMPOUND | 1 | 31-OCT-26 07.50.40.429397 PM |
| 7 | BEFORE STATEMENT | *null* | 31-OCT-26 07.50.40.431764 PM |
| 8 | AFTER ROW DELETE | 1 | 31-OCT-26 07.50.40.431932 PM |
| 9 | AFTER STATEMENT \/ COMPOUND | 1 | 31-OCT-26 07.50.40.432003 PM |

```sql
ROLLBACK TO before_trigger_demo;
```
```sql
SELECT name,type,line,text FROM user_errors WHERE name LIKE 'CW_%';
```
| NAME | TYPE | LINE | TEXT |
|:-----|:-----|-----:|:-----|

```sql
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
```
> ``` status
> 1 rows affected
> ```

```sql
SELECT * FROM cw_cursor_trace ORDER BY cursor_kind;
```
| CURSOR\_KIND | OBSERVED\_VALUE |
|:------------|:---------------|
| EXPLICIT | Computer Lab |
| FOR UPDATE CURRENT OF | 1 |
| IMPLICIT | 1 |
| PARAMETERIZED FOR LOOP | Computer Lab |
| STRONG REF CURSOR | Computer Lab |
| WEAK REF CURSOR | Computer Lab |

[fiddle](https://dbfiddle.uk/x6YRxBnX)
