# CampusWeave: complete syllabus companion
Vishwakarma Institute of Technology | Computer Engineering | AY 2026-27

This workbook connects every supplied syllabus topic to the timetable project. It distinguishes a working feature, an executed lab, a local simulation and an explanatory design. A simulation is not described as a deployed cluster. The Oracle scripts were separately executed on Oracle 21c in an approved CC0 db<>fiddle session; this does not imply that the Flask application uses Oracle.

## Unit 1: database foundations and modeling
### Need, evolution, concepts and design process
The starting file-based solution duplicates faculty names, room capacities and assignments across spreadsheets. A DBMS centralizes integrity, concurrent access, query processing and recovery. The evolution from hierarchical/network systems to relational systems, object-relational features and distributed NoSQL reflects changing workloads rather than a single universally best model.

CampusWeave uses SQL for authoritative scheduling facts and MongoDB for flexible feedback documents. Schema is the structure; an instance is its current data. Logical independence separates relational structure from application views; physical independence permits indexes without changing the query's meaning. External views include the faculty schedule; the conceptual layer contains entities/relationships; the internal layer contains InnoDB indexes, pages and logs.

The design process is requirements -> conceptual ER -> logical relations -> normalization -> physical indexes -> implementation -> verification. PROJECT_REPORT.md follows this sequence. ER_complete.svg covers the operational schema; ER_warehouse.svg covers the dimensional mart.

### ER, extended ER and relational model
Entities have keys and attributes; relationships have cardinality and participation. Faculty-course eligibility is M:N and becomes a junction table. Faculty's user-account participation is optional. A course offering participates in one division, one course and one eligible teacher pair.

An extended-ER interpretation specializes User into Admin, HOD, Coordinator, Faculty and Student by the role discriminator. The current enum stores one role per account, corresponding to disjoint specialization; all users require a role, making the discriminator total. Only the authenticated coordinator-style scheduling workflow is implemented; separate subtype portals are not claimed. If overlapping roles were needed, user_roles(user_id,role_id) would replace the single discriminator. Aggregation can treat a course offering (division-course-teacher association) as the object scheduled into a period.

The relational model represents tuples, domains, keys and referential integrity. SQL tables are bags unless uniqueness or DISTINCT removes duplicates. NULL represents missing/unknown values and requires IS NULL rather than equality comparisons.

### Codd's rules: a project interpretation
| Rule | Meaning and connection |
| --- | --- |
| 0 | Relational management: scheduling facts are managed through relational capabilities. |
| 1 | Information rule: facts are represented as values in relations. |
| 2 | Guaranteed access: table, primary key and column identify a value. |
| 3 | Systematic NULL handling: optional user linkage uses NULL explicitly. |
| 4 | Relational catalog: information_schema supplies the dictionary and diagrams. |
| 5 | Comprehensive language: SQL provides definitions, queries, integrity, privileges and transactions. |
| 6 | View updating: a simple checked view is updated in the SQL lab; arbitrary joined/aggregate views are not automatically updatable. |
| 7 | High-level operations: set-based UPDATE/DELETE and aggregation operate on multiple rows. |
| 8 | Physical independence: adding an index does not change query results. |
| 9 | Logical independence: views can hide some schema changes; not every change is transparent. |
| 10 | Integrity independence: keys/checks/triggers live in the database. |
| 11 | Distribution independence: a future distributed layer should preserve logical query behavior; the local system does not implement this rule across machines. |
| 12 | Nonsubversion: application routes cannot bypass SQL guards; unrestricted administrator access is outside that guarantee. |

This mapping explains the rules; it is not a claim that MySQL fully satisfies every Codd rule.

## Unit 2: dependencies, normalization and synthesis
The project report derives 1NF, 2NF and 3NF and lists actual candidate keys. Atomic fields eliminate repeating groups. Separating offering/run facts removes partial dependencies. Separating faculty, course, room and department descriptions removes transitive dependencies.

### Armstrong inference, closure and minimal cover
Reflexivity: if Y is a subset of X, then X -> Y. Augmentation: X -> Y implies XZ -> YZ. Transitivity: X -> Y and Y -> Z imply X -> Z. Union, decomposition and pseudotransitivity follow from these axioms.

The executed example has F = {A -> B, B -> C, A -> C, AB -> D}. Closure A+ is {A,B,C,D}, so A is a candidate key. In AB -> D, B is extraneous because A already determines B. A -> C is redundant through B. The minimal cover is {A -> B, B -> C, A -> D}. syllabus_lab.py computes these results rather than storing them as claimed outputs.

The 3NF synthesis groups dependencies by determinant, creates AB D and BC relations, removes subsumed relations and adds a candidate-key relation when none is present. For this example the output is R1(A,B,D), R2(B,C). It is dependency-preserving and lossless under the synthesis theorem because a key relation is retained. General decomposition is not automatically lossless merely because its tables have primary keys.

### Lossless join and dependency preservation
For a binary decomposition R -> R1,R2 under FDs, losslessness follows when the common attributes determine R1 or R2. Dependency preservation means the union of dependencies projected onto components implies the original FDs without joining relations. These are separate properties. The report's entity decompositions retain the determining key as the shared attribute.

### BCNF and its tradeoff
BCNF requires every determinant of a nontrivial FD to be a superkey. Consider R(Student,Course,Instructor), with (Student,Course) -> Instructor and Instructor -> Course. Candidate keys are (Student,Course) and (Student,Instructor). This can satisfy 3NF because Course is prime, but violates BCNF because Instructor is not a superkey. Decompose into InstructorCourse(Instructor,Course) and StudentInstructor(Student,Instructor). The decomposition is lossless because the intersection Instructor determines InstructorCourse, but the original (Student,Course) -> Instructor is not enforceable in either component alone. This is an educational counterexample, not an unannounced replacement of CampusWeave's schema.

### MVD and fourth normal form
Suppose a teacher's preferred days and preferred labs are independent: Faculty ->> Day and Faculty ->> Lab. Storing every (Faculty,Day,Lab) combination creates a cross product. Decompose into FacultyDay and FacultyLab to reach 4NF when the nontrivial MVD determinant is not a superkey. The executed lab reconstructs four combinations from two day rows and two lab rows and verifies equality. Independence is an explicit assumption; real course/lab compatibility must not be decomposed as if it were independent.

## Unit 3: query languages and procedural constructs
### Relational algebra to SQL
| Algebra expression (plain-text notation) | Equivalent SQL idea |
| --- | --- |
| sigma capacity >= 60 (rooms) | SELECT * FROM rooms WHERE capacity>=60 |
| pi room_code (rooms) | SELECT DISTINCT room_code FROM rooms |
| faculty JOIN department_id departments | Equijoin with ON or USING(department_id) |
| eligible_for_DBMS UNION eligible_for_DSA | Two compatible SELECT projections joined with UNION |
| all_faculty MINUS faculty_with_offerings | EXCEPT, or a correlated NOT EXISTS |
| rooms PRODUCT divisions followed by capacity selection | Non-equijoin ON rooms.capacity>=divisions.student_count |
| gamma subject_type, COUNT(*) (courses) | GROUP BY subject_type with COUNT(*) |

Projection in classical algebra removes duplicates; plain SELECT does not. SQL's NULL/three-valued logic also differs from classical two-valued relational algebra. The executable SQL showcase uses DISTINCT and explicit NULL tests where needed.

### SQL coverage and execution evidence
sql/07_syllabus_queries.sql executes 50 statements in an isolated database. It covers CREATE/ALTER, INSERT/UPDATE/DELETE, logical/conditional operators, LIKE/NOT LIKE, IN/NOT IN, BETWEEN, IS NULL/IS NOT NULL, ORDER BY, GROUP BY, aggregates and HAVING. It includes UNION/UNION ALL/INTERSECT/EXCEPT; string/date/time/numerical functions; equi/non-equi/self/outer joins; scalar/multirow/correlated subqueries; ANY/ALL/EXISTS; and DML with a subquery.

The simple lab_room_view updates its base table and WITH CHECK OPTION rejects a row that would leave the view. The multi-table faculty_schedule_view provides a reporting abstraction. Aggregation, DISTINCT, grouping and other constructs impose view-update restrictions; not every join view is universally read-only in every DBMS, so use the metadata and engine's rules rather than a blanket claim.

### DCL, roles, assertions, embedded and dynamic SQL
The SQL experiment creates a temporary non-login role, grants SELECT on its isolated schema, records SHOW GRANTS, revokes the privilege and removes the role. The actual app account is database-scoped; administrative passwords are kept in ignored runtime files. Role metadata in users is not the same thing as a database role.

TCL is exercised through START TRANSACTION, COMMIT, ROLLBACK, SAVEPOINT and ROLLBACK TO SAVEPOINT. SQL-standard CREATE ASSERTION is not supported by MySQL; the cross-row timetable assertion is implemented using procedures, triggers and locking. A trigger without a concurrency protocol alone would not prove race-free enforcement.

Python's connector calls are host-language database connectivity with bound parameters; they are not a precompiled EXEC SQL embedded-SQL language. Traditional embedded SQL uses host variables, a precompiler and SQLCA/status handling. The project provides the equivalent host-program query workflow through DB-API. The dynamic-SQL lab uses PREPARE, EXECUTE USING and DEALLOCATE; the UI's identifiers come from a fixed allowlist and values remain parameters.

### PL/SQL procedure, function, cursors and trigger types
The primary application executes MySQL procedures, triggers and fn_run_hours. Oracle syntax is supplied separately in sql/oracle/plsql_lab.sql and advanced_plsql.sql. The companion includes a stored publication procedure, utilization function, anonymous blocks, exception handling and DBMS_OUTPUT.

Cursor coverage includes implicit SQL cursor attributes; explicit OPEN/FETCH/CLOSE; parameterized cursors; cursor FOR loops; weak SYS_REFCURSOR and strong REF CURSOR types; and bound dynamic cursor SQL. Oracle also has FOR UPDATE cursors and WHERE CURRENT OF for row updates; an example is supplied below. These scripts were executed on Oracle 21c; oracle_execution.md records cursor trace rows, function results, expected exception handling and empty USER_ERRORS results.

Trigger coverage includes BEFORE row validation; AFTER INSERT/UPDATE/DELETE row events; BEFORE statement events; a compound trigger accumulating an affected-row count; AFTER statement processing; and INSTEAD OF UPDATE on a join view. Optional schema DDL auditing is shown but not installed. Database LOGON/LOGOFF/STARTUP/SHUTDOWN triggers require administrator scope and are intentionally not installed on a shared database.

## Unit 4: query processing, transactions, concurrency and recovery
Query processing parses and validates SQL, rewrites equivalent expressions, estimates costs from statistics, selects access paths/join orders and executes a physical plan. Predicate pushdown and projection pruning reduce work; indexed nested loops, hash joins or scans suit different cardinalities. Selecting every column can prevent a covering index from satisfying a query alone.

The 60,000-row controlled experiment compares the same result with and without a composite index. EXPLAIN changes from ALL/60,000 estimated rows to ref/one estimated row. evidence.json includes the complete plans and seven-sample medians. This is a reproducible microbenchmark, not a production capacity forecast.

### Transaction state diagram
Active -> Partially committed -> Committed is the successful path. A failure from Active or Partially committed leads to Failed -> Aborted, followed by restart or termination. A Python exception before commit invokes rollback. A database crash during commit requires recovery to decide the durable outcome; a client timeout does not by itself prove rollback.

ACID is demonstrated in the report: all-or-nothing persistence, constraint consistency, serialized writes and committed storage. Schedules interleave operations from multiple transactions. Conflict equivalence preserves the order of conflicting same-item operations from different transactions when at least one is a write. A precedence graph is conflict-serializable exactly when it is acyclic.

The executable graph lab gives a serializable T1 -> T2 example and a cyclic T1 <-> T2 example. View equivalence preserves initial reads, the precise write each read observes and final writers. W1(X), W2(X), W1(X) is view-serializable to T2,T1 but not conflict-serializable because of blind writes. The checker enumerates at most six transactions; it is a teaching tool, not a large schedule verifier.

### Concurrency protocols
Two-phase locking has a growing lock-acquisition phase and a shrinking release phase. Strict 2PL holds exclusive locks until commit/abort and simplifies recovery. CampusWeave's InnoDB row lock serializes supported writers until transaction completion. Timestamp ordering rejects operations that violate timestamp order; optimistic concurrency validates at commit; MVCC provides versioned reads. These alternatives are explained, not falsely claimed as custom implementations in this app.

Deadlocks require a cycle of waiting transactions and can be detected or prevented through consistent lock ordering. The app takes its global scheduling lock first. Concurrent publication tests prove that two drafts for one cohort cannot both win. Snapshot reads alone do not eliminate write skew; publication must revalidate under the write protocol.

### Recovery techniques
Write-ahead logging requires the relevant log information to be durable before a changed page is flushed. Undo restores uncommitted updates; redo reapplies committed changes that may not have reached data pages. Checkpoints bound recovery scanning. Shadow paging is an alternative approach with different fragmentation/concurrency tradeoffs. Backups plus log replay address failures beyond a single transaction.

The executed simplified recovery model undoes uncommitted T2's faculty-limit change and redoes committed T1's capacity change. Its recovered values are 16 and 65. This is not a claim of implementing ARIES or InnoDB crash recovery, nor a power-loss test.

## Unit 5: NoSQL, big data, Hadoop and warehousing
### NoSQL types, BASE and CAP
Key-value stores suit direct key lookup; document stores suit nested/variable records; wide-column stores suit partitioned sparse data; graph stores emphasize relationship traversal. Faculty feedback uses MongoDB documents with a tag array, rating, note and timestamps. The relational schedule remains the source of truth; no distributed transaction spans MySQL and MongoDB.

BASE means Basically Available, Soft state, Eventually consistent and describes a design tendency, not a mandatory property of every NoSQL product. MongoDB also supports stronger consistency and transactions in suitable topologies. CAP concerns the choice between linearizable consistency and availability during a network partition, not an unrestricted 'choose any two' rule. The local CAP simulation explicitly returns stale data in its AP branch and refuses a read in its CP branch, then reconciles replicas.

### Actual MongoDB work
The authenticated local MongoDB 8.0 database stores faculty_feedback. The Flask feedback screen implements create/read/update/delete through PyMongo and a live aggregation by subject. The isolated lab executes 16 operations: insertMany, find/count, equality, comparison, projection, array membership, sorting/limit, updateOne, updateMany, deleteOne, distinct, group/average/sum, compound indexing, hinted explain and regex filtering, plus actual mapReduce.

The legacy MapReduce result is compared with aggregation totals. MongoDB has deprecated MapReduce since version 5.0; it remains in this teaching lab only because the syllabus requests it. Production-oriented code uses the aggregation pipeline. See mongo_evidence.json for execution results and the official command reference at https://www.mongodb.com/docs/manual/reference/command/mapreduce/.

### Big data, HDFS and MapReduce
Big data discussions consider volume, velocity, variety, veracity and value. A timetable demo is not a big-data workload. HDFS separates NameNode metadata from DataNode block storage and replicates blocks for fault tolerance. The provided model places three replicas per block and calculates remaining replicas after a node failure. A real deployment also needs heartbeats, re-replication, rack awareness and operational management.

MapReduce maps input to key-value pairs, partitions and shuffles by key, then reduces grouped values. A combiner may reduce network traffic when its operation is valid. The local parallel experiment maps department fragments to hour totals, combines results and verifies equality with a serial calculation. Hadoop Streaming mapper/reducer scripts are supplied for use with a real Hadoop installation; they are also tested locally. No Hadoop cluster has been installed or benchmarked on this PC.

### Warehouse architecture and OLAP
The pipeline is operational sources -> extraction/staging -> transformation -> dimensional warehouse -> OLAP/reporting. The implemented MySQL teaching mart has dw_teaching_fact at one occupied published period per source entry, with subject, faculty, cohort and period dimensions. Idempotent loading uses the source entry key; repeated loads do not duplicate facts.

The star stores descriptive dimensions directly. A snowflake would normalize dimension hierarchies such as department; a fact constellation would share dimensions across teaching and room-maintenance facts. The current mart is a star, not all three schemas simultaneously. Dimensions are first-load snapshots; a production mart would define slowly changing dimensions and effective dates.

The warehouse screen performs ROLLUP across academic year, semester and subject type. Slice chooses a single dimension value; dice chooses multiple restrictions; drill-down shows finer detail; roll-up aggregates; pivot rotates categorical values into columns. Historical editions remain in the mart after archival, so its totals describe edition history and must not be confused with current room occupancy.

## Unit 6: parallel and distributed databases
Shared-memory architectures coordinate through common memory; shared-disk systems share storage with separate memory; shared-nothing systems partition both compute and storage. Local threads are not evidence of a shared-nothing cluster. I/O parallelism spreads reads across disks/partitions. Interquery parallelism runs independent queries simultaneously. Intraquery parallelism divides one query; intraoperation parallelism parallelizes one operator, while interoperation parallelism pipelines or overlaps different operators.

The local thread-pool aggregation illustrates intraoperation parallelism over two fragments. Concurrent publication tests illustrate independent client operations contending for one transactional resource. No speedup is claimed for Python threads; the purpose is decomposition and correctness.

Homogeneous distributed databases use the same engine; heterogeneous/federated systems integrate differing engines and schemas. MySQL plus MongoDB here is polyglot persistence on one PC, not a transparent federated distributed DBMS. Horizontal fragmentation partitions rows by a predicate; vertical fragmentation splits columns while retaining the reconstruction key; hybrid fragmentation combines them. Replication makes copies; partitioning splits data. The executable lab verifies horizontal union and vertical key-join reconstruction.

Distributed query processing localizes a global query to fragments, pushes filters/projections down, chooses join locations and may use semijoins to reduce transfer. Network cost and skew can dominate local CPU cost. A two-phase commit coordinator asks participants to prepare, then records and distributes commit/abort; prepared participants may block if the coordinator fails. CampusWeave deliberately does not pretend that independent MySQL and MongoDB writes form an atomic distributed transaction.

## Laboratory experiment checklist
| Lab | Supplied implementation / evidence | Verification status |
| --- | --- | --- |
| 1 DDL and DML | 01_schema.sql, 07_syllabus_queries.sql | Executed on MySQL; constraints and rollback tested. |
| 2 SELECT operators/functions/sets | 07_syllabus_queries.sql | Executed; output samples in sql_evidence.json. |
| 3 Joins/subqueries/DML subqueries/strategies | Query showcase, SQL lab, EXPLAIN benchmark | Executed. |
| 4 Views/base updates/restrictions | lab_room_view, active_room_catalog, reporting view | Base update and CHECK OPTION rejection executed. |
| 5 PL/SQL cursors | oracle/advanced_plsql.sql | Executed on Oracle 21c; six cursor variants produce trace rows. |
| 6 Procedures/functions | MySQL procedures and fn_run_hours; Oracle companion | MySQL and Oracle 21c companion executed. |
| 7 Trigger types | MySQL integrity/audit triggers; Oracle row/statement/compound/INSTEAD OF scripts | MySQL and Oracle 21c companion executed. |
| 8 MongoDB queries/aggregation/indexing/MapReduce | mongo_experiments.py; mongo_evidence.json | 16 operations executed, including actual legacy MapReduce. |
| 9 Relational connectivity | Flask + mysql-connector-python | Working application and integration tests. |
| 10 Non-relational connectivity | Flask + PyMongo feedback module | Actual CRUD and aggregation tested. |

## Two-tier and three-tier architecture
The normal browser -> Flask application -> MySQL/MongoDB flow is a logical three-tier architecture even though all tiers run on one PC. A two-tier example is scripts/two_tier_report.py, a Python client that directly connects to MySQL and prints faculty workload. Physical deployment count and logical tier count are different concepts.

## Evidence and honesty boundaries
The project demonstrates the complete supplied topic list through implemented features, executed labs, executed Oracle source and explicitly labeled teaching models. A real Hadoop/distributed cluster is not represented as deployed. The code and workbook give the examiner concrete material for each topic without destabilizing the simple faculty planner.
