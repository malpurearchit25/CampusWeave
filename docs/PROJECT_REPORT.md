# CampusWeave
## A faculty-friendly college timetable planning system
DBMS course project | Flask + MySQL 8.4 | Academic edition 2026-27

CampusWeave turns academic assignments into a validated weekly timetable. It combines a normalized relational schema, a bounded constraint solver, stored procedures, database triggers, and atomic publication. A faculty-oriented interface keeps routine scheduling separate from the DBMS demonstration lab.

This report describes the implemented system and its observed tests. It does not claim that a feasible schedule is globally optimal or that the project is ready for unrestricted internet deployment. Sample names and academic data are illustrative.

## 1. Requirement analysis
### Problem statement
Manual timetabling distributes the same academic facts across spreadsheets and informal messages. A faculty member may be assigned to two divisions simultaneously; a practical may be placed in an unsuitable room; changing one semester may invalidate another. The problem is to assign every required course session to a day, consecutive teaching periods, and a suitable room while respecting shared resources.

### Actors and boundaries
The demonstrated actor is an authenticated academic coordinator. The seeded admin account performs catalog management, generation, publication and archival. Faculty are scheduling resources and report consumers; separate faculty and student portals are outside the implemented scope. The users table retains role metadata, but this is not a complete multi-role authorization product.

The application runs on this PC at 127.0.0.1:5050. Its MySQL server listens only on 127.0.0.1:3307. One academic year is treated as one scheduling conflict domain: published semesters in the same year share room and faculty reservations. Independent date ranges, rotating weeks, electives and team teaching are not modeled.

### Functional requirements and acceptance criteria
| ID | Requirement | Observable acceptance criterion |
| --- | --- | --- |
| FR1 | Maintain academic entities | Create, inspect, edit and remove unreferenced catalog records through validated forms. |
| FR2 | Enforce teaching eligibility | An assignment requires an existing faculty-course pair through a composite foreign key. |
| FR3 | Generate all required sessions | A draft contains sessions_per_week times duration periods for every scoped offering. |
| FR4 | Avoid resource clashes | Faculty, division and room cannot overlap within a run or against another published run in the same year. |
| FR5 | Respect constraints | Availability, exact required laboratory type, capacity and combined workload are checked. |
| FR6 | Keep practicals together | Each session has a session_no and occupies consecutive one-hour teaching periods in one room and day. |
| FR7 | Spread repeated sessions | At most one session of an offering is placed on a given day. |
| FR8 | Publish safely | Database validation, status update and audit insertion succeed or roll back together. |
| FR9 | Preserve history | Published runs can be archived; their entries and source records remain protected. |
| FR10 | Explain and export | Weekly grid, selected-division print/PDF, whole-run CSV, workload and room occupancy reports are available. |
| FR11 | Demonstrate DBMS concepts | Live savepoint/rollback lab, procedure and trigger inventory, and measured EXPLAIN evidence are supplied. |

### Non-functional requirements
Consistency is enforced in MySQL as well as in the scheduler. All application writes use a shared scheduling lock to serialize configuration changes and publication. Form submissions use CSRF tokens; templates escape values; SQL values use bound parameters. Credentials are kept outside Git. The browser UI uses local fonts and assets, so the demonstration requires no CDN or external API.

The search has an eight-second/100,000-node budget and a 200-session limit. These are protective bounds, not proof of infeasibility when a limit is reached. The seeded semester-3 case contains 28 sessions and 32 occupied periods; tests verify complete generation.

## 2. Conceptual model and ER-to-relational mapping
The complete ER diagram is supplied as ER_complete.svg and ER_complete.png. Academic and scheduling detail diagrams provide larger views. They are generated from the installed MySQL metadata rather than an unrelated conceptual sketch. There are 14 business tables and one technical scheduling_lock table, plus five separate dimensional warehouse tables. timetable_entries is a flattened read-only projection and faculty_schedule_view is a reporting view; neither is a stored entity.

### Mapping rules
Strong entities become tables with surrogate primary keys and natural alternate keys where appropriate. A one-to-many relationship places its foreign key on the many side. A many-to-many faculty-course relationship becomes faculty_courses with composite primary key (faculty_id, course_id). The optional faculty-user link is represented by a nullable unique foreign key. No repeating comma-separated list is stored in a column.

| Parent / relationship | Child | Cardinality and implementation |
| --- | --- | --- |
| departments | faculty, courses, divisions, timetable_runs | One department to zero or many rows; each child requires one department. |
| users | faculty | Optional one-to-one; faculty.user_id is nullable and unique. |
| faculty and courses | faculty_courses | Many-to-many resolved through the pair key. |
| faculty_courses | course_offerings | One eligible pair to many offerings; composite foreign key enforces eligibility. |
| divisions and courses | course_offerings | Each offering references one division and one course; their pair is unique. |
| faculty and time_slots | faculty_unavailability | A faculty/day/slot triple is unique. |
| users | timetable_runs | One creator per run; creator can own many runs. |
| timetable_runs | timetable_sessions | One run contains many numbered teaching sessions. |
| course_offerings and rooms | timetable_sessions | Each session references one offering and room; day is stored once. |
| timetable_sessions and time_slots | timetable_periods | Each occupied-period row references one session and one teaching period. |
| timetable_runs and users | approval_history | Each status action records its run, actor and timestamp. |

The dictionary appendix lists every column, SQL type, nullability, primary/foreign key and alternate unique key. The diagram's question mark denotes a nullable field. A session is identified by (run_id, offering_id, session_no); its day and room are stored once in timetable_sessions. timetable_periods stores only entry_id, session_id and slot_id. The flattened timetable_entries view makes existing reports convenient without repeating stored facts.

## 3. Normalization through 3NF
### Begin with an unnormalized scheduling sheet
Imagine a row containing DivisionName, DepartmentName, AcademicYear, Semester, StudentCount, CourseCode, CourseName, FacultyCode, FacultyName, RoomCode, RoomCapacity and a list of weekly periods. Repeating period lists violate 1NF. Course titles, faculty names and room capacity are copied across many rows, creating update anomalies. Deleting the only scheduled occurrence of a room could also delete the only record of its capacity.

### First normal form
Expand the repeating period list into individual occupied-period rows. Each field contains one value. A candidate occurrence key is (RunID, OfferingID, Day, SlotID). This alone does not remove repeated course, faculty and room facts.

### Second normal form
In that flattened relation, OfferingID determines DivisionID, CourseID, FacultyID and weekly requirements. RunID determines the run's academic scope and status. These depend on only part of the composite occurrence key. Move them into course_offerings and timetable_runs. Separate a session header (run, offering, session number, room and day) from its individual slot allocations.

The faculty_courses relation has only its composite key and no non-key attributes, so no partial dependency exists. Single-column primary keys in the entity tables also have no partial primary-key dependency; this observation alone does not prove 3NF.

### Third normal form
Remove transitive descriptive dependencies: CourseID determines CourseName and SubjectType; FacultyID determines FacultyName and DepartmentID; DepartmentID determines DepartmentName; RoomID determines Capacity and RoomType; SlotID determines StartTime and EndTime. Store those attributes in their respective entity tables and reference them using foreign keys.

| Relation | Principal functional dependencies / candidate keys |
| --- | --- |
| departments | department_id -> department_name; department_name is an alternate key. |
| users | user_id -> username, password_hash, role, is_active; username is an alternate key. |
| faculty | faculty_id -> code, name, department, designation, max hours, optional user; faculty_code is an alternate key. The nullable user link is a conditional unique identifier, not an unconditional candidate key. |
| divisions | division_id -> all attributes; (division_name, department_id, academic_year, semester) is an alternate key. |
| courses | course_id -> code, name, department, type, default sessions, duration, required room type; course_code is an alternate key. |
| rooms | room_id -> code, name, type, capacity, active; room_code is an alternate key. |
| time_slots | slot_id -> start_time, end_time, slot_type; start_time and end_time are alternate keys under the enforced fixed-hour, unique-period rules. |
| faculty_courses | (faculty_id, course_id) is the key; no non-key attributes. |
| course_offerings | offering_id -> division, course, faculty, weekly sessions; (division_id, course_id) is an alternate key. |
| faculty_unavailability | unavailability_id -> faculty, day, slot; (faculty_id, day_of_week, slot_id) is an alternate key. |
| timetable_runs | run_id -> scope, status, creator, creation time, search_nodes. |
| timetable_sessions | session_id -> run, offering, session_no, room, day; (run_id, offering_id, session_no) is an alternate key. |
| timetable_periods | entry_id -> session_id, slot_id; (session_id, slot_id) is an alternate key. |
| approval_history | approval_id -> run, actor, action, comment, action time. |
| scheduling_lock | lock_id only; technical singleton used for serialization. |

The session/period split removes the dependency (run, offering, session_no) -> room, day from the occupied-period table. Keeping those repeated columns in each physical period row would violate 3NF. Repetition in a reporting view is harmless because it is derived. Under the stated business dependencies, each non-key attribute depends on a candidate key, the whole key, and no non-key determinant. The decomposed business relations satisfy 3NF. The design does not assert that all possible future college policies preserve these dependencies.

### Why two sessions_per_week columns are intentional
courses.sessions_per_week is the subject's default requirement. course_offerings.sessions_per_week is the actual requirement for one division. An offering may override the default; therefore CourseID does not determine the offering-level weekly requirement. These are different facts, not accidental duplicate storage. Scheduling and completeness checks use the offering value.

### Lossless decomposition and anomaly removal
Each entity decomposition retains the determining key as the common attribute: for example, the course projection and offering relation share CourseID, which is a key of courses. Joining them restores the descriptive data without inventing course identities. Foreign keys preserve referential integrity; the eligible pair dependency is preserved through a composite reference. A course-name correction is made once before the course is used in a saved edition. Saved editions protect referenced source records so their historical meaning cannot silently change.

## 4. SQL, stored procedures and triggers
The application uses MySQL stored SQL/PSM. Oracle PL/SQL is a different dialect. A separate, clearly labeled Oracle companion lab is included at sql/oracle/plsql_lab.sql. It demonstrates a capacity trigger, publication procedure, audit trigger, exception handling and transaction rollback. It is not a port of the complete application and has been executed on Oracle 21c in the approved CC0 db<>fiddle environment. The 42-batch evidence and public rerunnable link are included in oracle_execution.md.

### Relational SQL coverage
sql/04_query_showcase.sql contains multi-table joins, LEFT JOIN with zero-count handling, aggregation, HAVING, correlated NOT EXISTS, a reporting view, a CTE with DENSE_RANK, EXPLAIN and metadata inspection. The UI exercises INSERT, SELECT, UPDATE and DELETE for eligible catalog records. SQL values are parameterized; dynamic identifiers come only from the catalog allowlist.

### sp_validate_run
The validation procedure rejects an absent or empty run, missing assignments, incomplete weekly requirements, invalid academic scope, unsuitable or inactive rooms, unavailable faculty, malformed consecutive blocks, repeated same-day sessions, resource collisions and combined published workload overflow. It uses SIGNAL SQLSTATE '45000' to return domain errors to Flask. A valid call produces no result set.

### sp_publish_run
The publication procedure takes a run ID and actor ID. It locks the singleton scheduling row and target run, checks that the actor is an active coordinator-level account and that the run is a draft, rejects a second active timetable for the same cohort, calls validation, then updates status. It does not COMMIT internally: the caller owns the transaction, including the audit trigger's insert.

Example: START TRANSACTION; CALL sp_publish_run(1,1); COMMIT; Use an actual draft ID from the dashboard. A failed call must be followed by ROLLBACK in an interactive SQL client. The Python transaction context performs that rollback automatically.

### Trigger coverage
trg_session_insert guards session headers against invalid scope/session numbers, insufficient capacity and wrong room type. trg_validate_timetable_entry guards period allocations against unavailable faculty, break periods and same-run resource collisions. trg_entry_immutable prevents update-based bypass. trg_entry_delete protects published and archived entries. trg_run_transition checks permitted lifecycle transitions and revalidates publication. trg_run_audit records status changes automatically.

Catalog-history triggers reject changes to faculty, subjects, divisions, rooms or assignments used by saved schedules. Availability additions cannot contradict a published schedule; availability edits use remove-and-recreate. Period triggers reject overlapping times. Foreign keys reject deletion of referenced parent rows. Application management writes share the scheduling lock; unrestricted database-admin edits remain outside the supported UI workflow.

## 5. Query optimization and transaction processing
### Query optimization method
The normalized application indexes session headers by (run_id, day_of_week), (room_id, day_of_week), and offering; occupied periods have a unique (session_id, slot_id) index and a slot foreign-key index. The separate index microbenchmark uses a flattened synthetic table to isolate the effect of (run_id, day_of_week, slot_id). Scope indexes support department/year/semester and published-year lookups. Composite index ordering follows equality predicates used for timetable retrieval. Indexes consume storage and add write cost; they are not added to every column indiscriminately.

The benchmark script creates a uniquely named disposable database with 60,000 synthetic entry rows, executes the identical selective query seven times without the composite index, adds the index, analyzes the table, then repeats the measurement. Both variants return exactly one row. The isolated database is removed afterward. The report's evidence appendix contains the actual EXPLAIN plans, estimated rows and median wall-clock timings from this PC.

The unindexed plan uses ALL and estimates 60,000 rows. The indexed plan uses ref and estimates one row. Timings are environment- and cache-dependent; the test demonstrates index access selection rather than a universal speed guarantee. The small seeded production dataset may reasonably choose different plans.

### Atomicity
Generation inserts one run and all its entries within a single transaction. If a trigger rejects an entry, the exception rolls back the entire operation. Publication updates the run and inserts history through a trigger in the same transaction. A test deliberately inserts a valid entry followed by a conflicting entry and verifies that neither the run nor its earlier entry remains.

### Consistency
Primary keys, foreign keys, unique constraints, CHECK constraints, validation procedures and triggers enforce domain invariants. The scheduler plans constraints in memory; the database independently rechecks the persisted result. Completeness is checked at publication because an intermediate insertion state is necessarily incomplete.

### Isolation and concurrency
InnoDB provides transactional row locks. All application mutations acquire SELECT ... FOR UPDATE on scheduling_lock(lock_id=1). Generation holds this lock through planning and persistence; the search budget limits how long it can block other writers. Publication revalidates while holding the same lock. A two-connection concurrent publication test starts with two valid drafts for the same cohort and verifies exactly one publication and one audit record.

The coarse lock is a deliberate demonstration-scale tradeoff: easy-to-explain correctness over maximum parallel throughput. A larger institution would partition locks by conflict domain and implement deadlock retry. Readers may view drafts during planning but cannot use a stale browser validation result to bypass publication-time checks.

### Durability and savepoints
Successful transactions call COMMIT and persist in InnoDB. Durability also depends on server configuration and storage; this project does not claim a power-loss test. The DBMS Lab inserts a temporary department, creates a savepoint, inserts a second department, rolls back the second insert, then rolls back the entire transaction. Counts observed at each stage are 1, 1 and 0. No experiment records remain.

## 6. Architecture and application functionality
The architecture diagram separates the browser, Flask/Waitress request layer, bounded scheduler and MySQL persistence. app.py handles HTTP requests and renders Jinja templates. catalog.py defines the only allowed entities and fields. db.py manages parameter binding, connection lifetime and commit/rollback. scheduler.py reads constraints, constructs a feasible plan and persists it atomically.

### Scheduling algorithm
Expand each offering into numbered sessions. Sort long blocks first. Enumerate days ordered by the current division's daily load, then contiguous teaching blocks and suitable rooms. Reject blocked faculty periods, over-limit workload and overlapping faculty/division/room reservations. Repeated sessions of the same offering use different days. Backtrack when a placement blocks a later task. The first complete feasible assignment is returned; search budget exhaustion is reported separately from a proven exhausted search.

One-hour periods make occupied-period counts equal teaching hours. A practical requires its configured room type rather than any arbitrary lab. Published runs in the same academic year reserve resources across all departments and semesters. A new draft is not itself a reservation; two drafts may coexist, but publication rechecks their conflicts.

### User workflow
Sign in using the local demo account. Review assignments and faculty eligibility. Select a cohort and generate a draft. Inspect the weekly grid by division; multi-period sessions are shown as a single spanning block. Publish after review. Export CSV for all divisions or print the selected division to PDF. Insights reports only published hours in the selected academic year. Archive a published edition to release reservations while retaining its history.

### Interface and security decisions
The faculty interface uses navy, blue, ivory and restrained gold. Subject colors support scanning without being the only source of meaning; each cell also names its subject and room. Form labels, keyboard focus, a skip link, readable errors, mobile navigation and a print layout support everyday use. Server-side validation remains authoritative.

Passwords are stored as hashes. The demo password is intentionally documented for local evaluation, not a production secret. Sessions use HttpOnly and SameSite=Lax cookies; POST forms require CSRF tokens. Templates escape untrusted values, CSV text is guarded against formula injection, and a Content Security Policy limits resources to the local application. The server binds to loopback. Public hosting would require separate deployment, stronger account management, HTTPS and additional review.

## 7. Verification and results
The supplied pytest suite creates a fresh, uniquely named database per test. It never resets the user's application database. Tests cover valid generation, empty/incomplete schedules, wrong lab type, unavailable faculty, duplicate resource allocation, update bypass, failed multi-write rollback, protected source records, cross-semester scheduling, concurrent publication, archival, immutable published entries, infeasible workload, overlapping periods and eligibility foreign keys.

Web tests cover all main pages, CSRF rejection, login, output escaping, catalog create/edit/delete, savepoint cleanup, publishing through the stored procedure, CSV row counts, missing-run handling and draft exclusion from analytics. The evidence appendix records the actual final test count and elapsed time. A test checklist without execution is not presented as a passed test.

Browser review covers desktop and narrow layouts, sign-in, cohort selection, generation, timetable review and publication confirmation. Screenshots in the submission package show the implemented UI. The complete ER and dictionary are extracted from the application schema. Oracle companion execution is separately verified on Oracle 21c; its results are kept distinct from the local MySQL/MongoDB test suite.

## 8. Demonstration plan and viva preparation
### Eight-minute demonstration
1. Introduce the scheduling problem and three resource constraints: faculty, division and room.
2. Show the ER overview and explain the faculty_courses junction plus composite eligibility foreign key.
3. Explain one normalization example: RoomID determines capacity, so room facts belong in rooms rather than every timetable entry.
4. Open the academic assignments and generate semester 3 in a fresh installation (or semester 5 if the prepared semester 3 example is already published). Point out the two-hour practical blocks and separate-day course sessions.
5. Publish the run. Show the audit history and explain the procedure-trigger-transaction chain.
6. Generate semester 5 and explain how existing published faculty and room reservations are respected.
7. Run the live savepoint/rollback experiment; show 1, 1, 0 and the installed trigger inventory.
8. Show the EXPLAIN comparison and automated test report. End with limitations and feasible future work.

### Viva questions and concise answers
| Question | Answer |
| --- | --- |
| Why use a relational database? | Shared academic facts have explicit relationships, keys and consistency rules; transactions keep related changes atomic. |
| Why a junction table? | Faculty and courses are many-to-many. The pair key prevents duplicate eligibility records. |
| Why a composite foreign key in offerings? | Two separate foreign keys prove that a faculty and course exist; the composite reference proves that the faculty is eligible for that course. |
| What is 3NF? | For each nontrivial dependency X -> A, X is a superkey or A is prime. The documented business relations avoid non-key transitive dependencies. |
| Why keep default and offering weekly counts? | A subject default and a division-specific requirement are different facts. Scheduling uses the latter. |
| Procedure versus trigger? | A procedure is called explicitly, for example publication. A trigger runs automatically on its table event, for example audit insertion. |
| Why validate both in Python and SQL? | Python avoids bad placements efficiently; SQL protects persisted integrity and rechecks at the publication boundary. |
| What happens after the fifth insert fails? | The transaction context rolls back earlier inserts, including the new run. |
| What does FOR UPDATE do? | It locks selected rows until transaction completion so competing supported writers serialize. |
| Why validate again at publish? | Another timetable may have been published after a draft was generated or displayed. |
| Why not COMMIT inside the procedure? | The caller must control the entire atomic unit, including related changes and audit work. |
| Why is the composite index useful? | Equality predicates on its leading columns narrow the search to matching entries instead of scanning the table. |
| Does an index always improve a query? | No. Selectivity, table size, statistics, write cost and query shape matter. EXPLAIN must be inspected. |
| Is the schedule optimal? | It is a feasible solution under the declared constraints; no global optimality claim is made. |
| Why keep session_no? | It distinguishes one multi-period session from another and allows completeness/contiguity checks. |
| How is room utilization computed? | Published occupied hours divided by teaching periods times six days, for the selected academic year. |
| What is a savepoint? | A named point inside a transaction that permits partial rollback without ending the transaction. |
| Is MySQL PL/SQL? | No. This application uses MySQL stored SQL. The separate Oracle lab uses PL/SQL syntax and must be run on Oracle. |

## 9. Limitations, future work and references
This local project supports fixed one-hour periods, one teacher per offering, six teaching days, up to six sessions per offering per week and at most 200 sessions per generated run. It omits calendar-date exceptions, multi-campus travel, student electives, team teaching, multi-role portals and optimization objectives such as minimizing gaps. Saved academic editions intentionally constrain catalog edits to preserve history. A frozen edition is replaced using new academic records, not silently rewritten.

Future work could add date-bounded terms, faculty-specific preference scoring, CP-SAT optimization, dedicated approval roles, schema migrations and scoped reservation locks. These are extensions, not features claimed as complete.

References: MySQL 8.4 Reference Manual (https://dev.mysql.com/doc/refman/8.4/en/); Connector/Python transaction documentation (https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlconnection-start-transaction.html); Oracle PL/SQL error handling (https://docs.oracle.com/en/database/oracle/oracle-database/21/lnpls/plsql-error-handling.html); Graphviz (https://graphviz.org/). The supplied source, metadata dictionary, test output and benchmark JSON are the primary evidence for project-specific claims.
