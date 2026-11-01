"""Allowlisted form definitions; table/column identifiers never come from raw input."""
def field(name,label,kind='text',choices=None): return dict(name=name,label=label,kind=kind,choices=choices)
DEPTS=('departments','department_id','department_name')
FAC=('faculty','faculty_id','faculty_name')
COURSES=('courses','course_id','course_name')
DIVS=('divisions','division_id','division_name')
SLOTS=('time_slots','slot_id','start_time')
ROOM_TYPES=['CLASSROOM','COMPUTER_LAB','ELECTRONICS_LAB','OTHER_LAB']
CATALOG={
 'faculty':dict(title='Faculty',singular='faculty member',pk='faculty_id',fields=[field('faculty_code','Code'),field('faculty_name','Name'),field('department_id','Department','select',DEPTS),field('designation','Designation'),field('max_weekly_hours','Weekly hour limit','number')]),
 'courses':dict(title='Subjects',singular='subject',pk='course_id',fields=[field('course_code','Code'),field('course_name','Subject name'),field('department_id','Department','select',DEPTS),field('subject_type','Type','select',['THEORY','PRACTICAL','TUTORIAL']),field('sessions_per_week','Default sessions / week','number'),field('session_duration_slots','Hours / session','number'),field('required_room_type','Required room','optional',ROOM_TYPES)]),
 'divisions':dict(title='Divisions',singular='division',pk='division_id',fields=[field('division_name','Name'),field('department_id','Department','select',DEPTS),field('academic_year','Academic year'),field('semester','Semester','number'),field('student_count','Students','number')]),
 'rooms':dict(title='Rooms',singular='room',pk='room_id',fields=[field('room_code','Code'),field('room_name','Name'),field('room_type','Room type','select',ROOM_TYPES),field('capacity','Capacity','number'),field('is_active','Available','select',['1','0'])]),
 'course_offerings':dict(title='Assignments',singular='assignment',pk='offering_id',fields=[field('division_id','Division','select',DIVS),field('course_id','Subject','select',COURSES),field('faculty_id','Faculty','select',FAC),field('sessions_per_week','Sessions / week','number')]),
 'faculty_courses':dict(title='Eligibility',singular='eligible pair',pk=None,fields=[field('faculty_id','Faculty','select',FAC),field('course_id','Subject','select',COURSES)]),
 'faculty_unavailability':dict(title='Availability',singular='unavailable period',pk='unavailability_id',fields=[field('faculty_id','Faculty','select',FAC),field('day_of_week','Unavailable day','select',['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY']),field('slot_id','Period','select',SLOTS)]),
 'departments':dict(title='Departments',singular='department',pk='department_id',fields=[field('department_name','Name')]),
 'time_slots':dict(title='Periods',singular='period',pk='slot_id',fields=[field('start_time','Starts','time'),field('end_time','Ends','time'),field('slot_type','Type','select',['TEACHING','BREAK'])])}
