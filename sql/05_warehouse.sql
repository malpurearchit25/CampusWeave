-- Separate dimensional mart. Fact grain: one occupied period in a published run.
CREATE TABLE dw_subject(subject_key INT PRIMARY KEY,course_code VARCHAR(20),course_name VARCHAR(100),subject_type VARCHAR(20));
CREATE TABLE dw_faculty(faculty_key INT PRIMARY KEY,faculty_name VARCHAR(100),department_name VARCHAR(100));
CREATE TABLE dw_cohort(cohort_key INT PRIMARY KEY,division_name VARCHAR(30),department_name VARCHAR(100),academic_year VARCHAR(20),semester INT);
CREATE TABLE dw_period(period_key INT PRIMARY KEY,start_time TIME,end_time TIME,slot_type VARCHAR(20));
CREATE TABLE dw_teaching_fact(source_entry_id INT PRIMARY KEY,run_id INT NOT NULL,subject_key INT NOT NULL,
 faculty_key INT NOT NULL,cohort_key INT NOT NULL,period_key INT NOT NULL,day_of_week VARCHAR(12),teaching_hours DECIMAL(4,1) NOT NULL,
 loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(subject_key) REFERENCES dw_subject(subject_key),FOREIGN KEY(faculty_key) REFERENCES dw_faculty(faculty_key),
 FOREIGN KEY(cohort_key) REFERENCES dw_cohort(cohort_key),FOREIGN KEY(period_key) REFERENCES dw_period(period_key));
CREATE INDEX idx_dw_cohort_subject ON dw_teaching_fact(cohort_key,subject_key);
