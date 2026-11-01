-- MySQL 8.4. Run inside a NEW empty database. No DROP DATABASE statements.
CREATE TABLE departments(
 department_id INT AUTO_INCREMENT PRIMARY KEY,
 department_name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE users(
 user_id INT AUTO_INCREMENT PRIMARY KEY,
 username VARCHAR(50) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 role ENUM('ADMIN','HOD','COORDINATOR','FACULTY','STUDENT') NOT NULL,
 is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE faculty(
 faculty_id INT AUTO_INCREMENT PRIMARY KEY,
 faculty_code VARCHAR(20) NOT NULL UNIQUE,
 faculty_name VARCHAR(100) NOT NULL,
 department_id INT NOT NULL,
 designation VARCHAR(50),
 max_weekly_hours DECIMAL(4,1) NOT NULL DEFAULT 18,
 user_id INT UNIQUE,
 FOREIGN KEY(department_id) REFERENCES departments(department_id),
 FOREIGN KEY(user_id) REFERENCES users(user_id),
 CHECK(max_weekly_hours>0)
);
CREATE TABLE divisions(
 division_id INT AUTO_INCREMENT PRIMARY KEY,
 division_name VARCHAR(30) NOT NULL,
 department_id INT NOT NULL,
 academic_year VARCHAR(20) NOT NULL,
 semester INT NOT NULL,
 student_count INT NOT NULL,
 FOREIGN KEY(department_id) REFERENCES departments(department_id),
 UNIQUE(division_name,department_id,academic_year,semester),
 CHECK(semester BETWEEN 1 AND 8), CHECK(student_count>0)
);
CREATE TABLE courses(
 course_id INT AUTO_INCREMENT PRIMARY KEY,
 course_code VARCHAR(20) NOT NULL UNIQUE,
 course_name VARCHAR(100) NOT NULL,
 department_id INT NOT NULL,
 subject_type ENUM('THEORY','PRACTICAL','TUTORIAL') NOT NULL,
 sessions_per_week INT NOT NULL,
 session_duration_slots INT NOT NULL DEFAULT 1,
 required_room_type ENUM('CLASSROOM','COMPUTER_LAB','ELECTRONICS_LAB','OTHER_LAB') NULL,
 FOREIGN KEY(department_id) REFERENCES departments(department_id),
 CHECK(sessions_per_week BETWEEN 1 AND 6), CHECK(session_duration_slots BETWEEN 1 AND 3), CHECK(subject_type<>'PRACTICAL' OR required_room_type IS NOT NULL)
);
CREATE TABLE rooms(
 room_id INT AUTO_INCREMENT PRIMARY KEY,
 room_code VARCHAR(20) NOT NULL UNIQUE,
 room_name VARCHAR(100) NOT NULL,
 room_type ENUM('CLASSROOM','COMPUTER_LAB','ELECTRONICS_LAB','OTHER_LAB') NOT NULL,
 capacity INT NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE,
 CHECK(capacity>0)
);
CREATE TABLE time_slots(
 slot_id INT AUTO_INCREMENT PRIMARY KEY,
 start_time TIME NOT NULL, end_time TIME NOT NULL,
 slot_type ENUM('TEACHING','BREAK') NOT NULL DEFAULT 'TEACHING',
 CHECK(TIME_TO_SEC(end_time)-TIME_TO_SEC(start_time)=3600), UNIQUE(start_time), UNIQUE(end_time)
);
CREATE TABLE faculty_courses(
 faculty_id INT NOT NULL, course_id INT NOT NULL,
 PRIMARY KEY(faculty_id,course_id),
 FOREIGN KEY(faculty_id) REFERENCES faculty(faculty_id),
 FOREIGN KEY(course_id) REFERENCES courses(course_id)
);
CREATE TABLE course_offerings(
 offering_id INT AUTO_INCREMENT PRIMARY KEY,
 division_id INT NOT NULL, course_id INT NOT NULL, faculty_id INT NOT NULL,
 sessions_per_week INT NOT NULL,
 FOREIGN KEY(division_id) REFERENCES divisions(division_id),
 FOREIGN KEY(course_id) REFERENCES courses(course_id),
 FOREIGN KEY(faculty_id,course_id) REFERENCES faculty_courses(faculty_id,course_id),
 UNIQUE(division_id,course_id), CHECK(sessions_per_week BETWEEN 1 AND 6)
);
CREATE TABLE faculty_unavailability(
 unavailability_id INT AUTO_INCREMENT PRIMARY KEY,
 faculty_id INT NOT NULL,
 day_of_week ENUM('MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY') NOT NULL,
 slot_id INT NOT NULL,
 FOREIGN KEY(faculty_id) REFERENCES faculty(faculty_id),
 FOREIGN KEY(slot_id) REFERENCES time_slots(slot_id),
 UNIQUE(faculty_id,day_of_week,slot_id)
);
CREATE TABLE timetable_runs(
 run_id INT AUTO_INCREMENT PRIMARY KEY,
 department_id INT NOT NULL, academic_year VARCHAR(20) NOT NULL, semester INT NOT NULL,
 status ENUM('DRAFT','PUBLISHED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
 search_nodes INT NOT NULL DEFAULT 0, created_by INT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(department_id) REFERENCES departments(department_id),
 FOREIGN KEY(created_by) REFERENCES users(user_id)
);
CREATE TABLE timetable_sessions(
 session_id INT AUTO_INCREMENT PRIMARY KEY,
 run_id INT NOT NULL, offering_id INT NOT NULL, session_no INT NOT NULL,
 room_id INT NOT NULL,
 day_of_week ENUM('MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY') NOT NULL,
 FOREIGN KEY(run_id) REFERENCES timetable_runs(run_id),
 FOREIGN KEY(offering_id) REFERENCES course_offerings(offering_id),
 FOREIGN KEY(room_id) REFERENCES rooms(room_id),
 UNIQUE(run_id,offering_id,session_no),
 INDEX idx_session_run_day(run_id,day_of_week),
 INDEX idx_session_room_day(room_id,day_of_week)
);
CREATE TABLE timetable_periods(
 entry_id INT AUTO_INCREMENT PRIMARY KEY,
 session_id INT NOT NULL, slot_id INT NOT NULL,
 FOREIGN KEY(session_id) REFERENCES timetable_sessions(session_id),
 FOREIGN KEY(slot_id) REFERENCES time_slots(slot_id),
 UNIQUE(session_id,slot_id)
);
-- Read-only flattened projection. Repeated descriptive facts live in the VIEW, not stored rows.
CREATE VIEW timetable_entries AS
SELECT p.entry_id,s.session_id,s.run_id,s.offering_id,s.session_no,s.room_id,s.day_of_week,p.slot_id
FROM timetable_periods p JOIN timetable_sessions s USING(session_id);
CREATE TABLE approval_history(
 approval_id INT AUTO_INCREMENT PRIMARY KEY, run_id INT NOT NULL, action_by INT NOT NULL,
 action ENUM('PUBLISHED','ARCHIVED') NOT NULL,
 comments VARCHAR(500), action_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(run_id) REFERENCES timetable_runs(run_id),
 FOREIGN KEY(action_by) REFERENCES users(user_id)
);

-- Departments
INSERT INTO departments(department_name) VALUES
('Computer Engineering'),('Electronics and Telecommunication'),('Mechanical Engineering');
-- Demo actor used by timetable_runs.created_by. This is NOT an authenticated login.
INSERT INTO users(username,password_hash,role) VALUES
('admin','SET_BY_SETUP','ADMIN');

-- Faculty
INSERT INTO faculty(faculty_code,faculty_name,department_id,designation,max_weekly_hours) VALUES
('F001','Asha Sharma',1,'Assistant Professor',16),
('F002','Rahul Patil',1,'Associate Professor',18),
('F003','Neha Joshi',1,'Assistant Professor',16),
('F004','Kiran Deshmukh',1,'Assistant Professor',16),
('F005','Priya Kulkarni',1,'Assistant Professor',16),
('F006','Sanjay More',1,'Associate Professor',18);

-- Divisions
INSERT INTO divisions(division_name,department_id,academic_year,semester,student_count) VALUES
('SE-A',1,'2026-27',3,60),('SE-B',1,'2026-27',3,55),('TE-A',1,'2026-27',5,58);

-- Courses
INSERT INTO courses(course_code,course_name,department_id,subject_type,sessions_per_week,session_duration_slots,required_room_type) VALUES
('DBMS','Database Management Systems',1,'THEORY',3,1,NULL),
('DSA','Data Structures and Algorithms',1,'THEORY',3,1,NULL),
('DBMSL','Database Management Systems Lab',1,'PRACTICAL',1,2,'COMPUTER_LAB'),
('OS','Operating Systems',1,'THEORY',3,1,NULL),
('MATH','Discrete Mathematics',1,'THEORY',3,1,NULL),
('PYLAB','Python Programming Lab',1,'PRACTICAL',1,2,'COMPUTER_LAB'),
('CN','Computer Networks',1,'THEORY',3,1,NULL),
('SE','Software Engineering',1,'THEORY',2,1,NULL);

-- Rooms
INSERT INTO rooms(room_code,room_name,room_type,capacity) VALUES
('A101','Classroom A-101','CLASSROOM',70),
('A102','Classroom A-102','CLASSROOM',65),
('A103','Classroom A-103','CLASSROOM',60),
('B201','Classroom B-201','CLASSROOM',90),
('LAB1','Computer Lab 1','COMPUTER_LAB',65),
('LAB2','Computer Lab 2','COMPUTER_LAB',60),
('ELAB1','Electronics Lab 1','ELECTRONICS_LAB',60);

-- Slots: lunch is omitted from teaching-slot candidates by slot_type
INSERT INTO time_slots(start_time,end_time,slot_type) VALUES
('09:00:00','10:00:00','TEACHING'),
('10:00:00','11:00:00','TEACHING'),
('11:00:00','12:00:00','TEACHING'),
('12:00:00','13:00:00','BREAK'),
('13:00:00','14:00:00','TEACHING'),
('14:00:00','15:00:00','TEACHING'),
('15:00:00','16:00:00','TEACHING');

-- Faculty eligible to teach courses
INSERT INTO faculty_courses(faculty_id,course_id) VALUES
(1,1),(1,5),(2,2),(2,4),(3,3),(3,6),(4,7),(4,8),(5,1),(5,8),(6,2),(6,4),(6,7);

-- Course offering per division. Weekly requirements are configured here.
INSERT INTO course_offerings(division_id,course_id,faculty_id,sessions_per_week) VALUES
(1,1,1,3),(1,2,2,3),(1,3,3,1),(1,4,2,3),(1,5,1,3),(1,6,3,1),
(2,1,5,3),(2,2,6,3),(2,3,3,1),(2,4,6,3),(2,5,1,3),(2,6,3,1),
(3,7,4,3),(3,8,5,2),(3,2,6,3),(3,4,2,3);

-- Faculty unavailable slots
INSERT INTO faculty_unavailability(faculty_id,day_of_week,slot_id) VALUES
(1,'MONDAY',2),(2,'FRIDAY',6),(3,'WEDNESDAY',1),(4,'THURSDAY',5);

-- View for reporting
CREATE VIEW faculty_schedule_view AS
SELECT tr.run_id,tr.status,f.faculty_code,f.faculty_name,c.course_code,c.course_name,
       d.division_name,r.room_code,te.day_of_week,ts.start_time,ts.end_time
FROM timetable_entries te
JOIN timetable_runs tr ON te.run_id=tr.run_id
JOIN course_offerings co ON te.offering_id=co.offering_id
JOIN faculty f ON co.faculty_id=f.faculty_id
JOIN courses c ON co.course_id=c.course_id
JOIN divisions d ON co.division_id=d.division_id
JOIN rooms r ON te.room_id=r.room_id
JOIN time_slots ts ON te.slot_id=ts.slot_id;


CREATE TABLE scheduling_lock(lock_id INT PRIMARY KEY);
INSERT INTO scheduling_lock VALUES(1);
CREATE INDEX idx_division_scope ON divisions(department_id,academic_year,semester);
CREATE INDEX idx_run_scope ON timetable_runs(academic_year,status,department_id,semester);
CREATE INDEX idx_faculty_entries ON course_offerings(faculty_id,offering_id);
