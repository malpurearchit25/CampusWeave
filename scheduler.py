"""Deterministic bounded backtracking; actual clock intervals, not slot IDs."""
from collections import defaultdict
from time import monotonic
from db import transaction, rows, execute, call, lock_catalog

DAYS = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY']

def solve(offerings, rooms, slots, unavailable, limits, reservations=(), budget=8):
    started = monotonic()
    occupied = defaultdict(list)
    hours = defaultdict(float)
    for e in reservations:
        for kind, key in [('f',e['faculty_id']),('r',e['room_id'])]:
            occupied[kind,key,e['day_of_week']].append((e['start_time'],e['end_time']))
        hours[e['faculty_id']] += (e['end_time']-e['start_time']).total_seconds()/3600
    tasks=[]
    for o in offerings:
        tasks.extend([{**o,'session_no':n} for n in range(1,o['sessions_per_week']+1)])
    required=defaultdict(float)
    for t in tasks:
        required[t['faculty_id']] += t['session_duration_slots']
    # All configured teaching periods are one hour, enforced by the schema.
    for fid, count in required.items():
        if count+hours[fid] > limits[fid]:
            raise ValueError('Faculty workload exceeds its weekly limit, including published timetables.')
    tasks.sort(key=lambda t:(-t['session_duration_slots'],t['offering_id'],t['session_no']))
    if len(tasks)>200:
        raise ValueError('This classroom demo supports up to 200 sessions per run.')
    picked=[]; daily=defaultdict(int); course_days=set(); nodes=0
    def search(i):
        nonlocal nodes
        nodes+=1
        if monotonic()-started>budget or nodes>100000:
            raise ValueError('Search budget reached. Relax availability, add rooms, or increase faculty capacity.')
        if i==len(tasks): return True
        t=tasks[i]; duration=t['session_duration_slots']
        eligible=[r for r in rooms if r['capacity']>=t['student_count'] and
            (r['room_type']==t['required_room_type'] if t['required_room_type'] else True)]
        eligible.sort(key=lambda r:(r['room_type']!='CLASSROOM' if not t['required_room_type'] else False,r['capacity'],r['room_id']))
        for day in sorted(DAYS,key=lambda d:(daily[t['division_id'],d],DAYS.index(d))):
            if (t['offering_id'],day) in course_days: continue
            for j in range(len(slots)-duration+1):
                block=slots[j:j+duration]
                if any(a['end_time']!=b['start_time'] for a,b in zip(block,block[1:])): continue
                start,end=block[0]['start_time'],block[-1]['end_time']
                if any((t['faculty_id'],day,s['slot_id']) in unavailable for s in block): continue
                keys=[('f',t['faculty_id'],day),('d',t['division_id'],day)]
                if any(start<b and end>a for k in keys for a,b in occupied[k]): continue
                for room in eligible:
                    rk=('r',room['room_id'],day)
                    if any(start<b and end>a for a,b in occupied[rk]): continue
                    for k in keys+[rk]: occupied[k].append((start,end))
                    daily[t['division_id'],day]+=duration;course_days.add((t['offering_id'],day))
                    picked.append((t,day,block,room))
                    if search(i+1): return True
                    picked.pop();course_days.remove((t['offering_id'],day));daily[t['division_id'],day]-=duration
                    for k in keys+[rk]: occupied[k].pop()
        return False
    if not search(0): raise ValueError('No feasible timetable. Check room type/capacity, availability and the six-day session limit.')
    return picked, {'nodes':nodes,'seconds':round(monotonic()-started,3),'sessions':len(tasks)}

def generate(department, year, semester, actor):
    with transaction() as cn:
        lock_catalog(cn)
        if rows(cn,"SELECT run_id FROM timetable_runs WHERE department_id=%s AND academic_year=%s AND semester=%s AND status='PUBLISHED'",(department,year,semester)):
            raise ValueError('Archive the published timetable for this cohort before generating its replacement.')
        offerings=rows(cn,'''SELECT co.*,c.subject_type,c.session_duration_slots,c.required_room_type,d.student_count
            FROM course_offerings co JOIN divisions d USING(division_id) JOIN courses c USING(course_id)
            WHERE d.department_id=%s AND d.academic_year=%s AND d.semester=%s''',(department,year,semester))
        if not offerings: raise ValueError('No course assignments for this selection. Add assignments in Academic data.')
        missing=rows(cn,'''SELECT division_name FROM divisions d WHERE department_id=%s AND academic_year=%s AND semester=%s
            AND NOT EXISTS(SELECT 1 FROM course_offerings co WHERE co.division_id=d.division_id)''',(department,year,semester))
        if missing: raise ValueError('Some divisions have no course assignments: '+', '.join(x['division_name'] for x in missing))
        rooms=rows(cn,'SELECT * FROM rooms WHERE is_active=1')
        slots=rows(cn,"SELECT * FROM time_slots WHERE slot_type='TEACHING' ORDER BY start_time")
        unavailable={(x['faculty_id'],x['day_of_week'],x['slot_id']) for x in rows(cn,'SELECT * FROM faculty_unavailability')}
        limits={x['faculty_id']:float(x['max_weekly_hours']) for x in rows(cn,'SELECT * FROM faculty')}
        reserved=rows(cn,'''SELECT co.faculty_id,te.room_id,te.day_of_week,ts.start_time,ts.end_time
            FROM timetable_entries te JOIN timetable_runs tr USING(run_id) JOIN course_offerings co USING(offering_id)
            JOIN time_slots ts USING(slot_id) WHERE tr.status='PUBLISHED' AND tr.academic_year=%s''',(year,))
        plan,stats=solve(offerings,rooms,slots,unavailable,limits,reserved)
        run=execute(cn,"INSERT INTO timetable_runs(department_id,academic_year,semester,created_by,search_nodes) VALUES(%s,%s,%s,%s,%s)",(department,year,semester,actor,stats['nodes']))
        for task,day,block,room in plan:
            sid=execute(cn,'INSERT INTO timetable_sessions(run_id,offering_id,session_no,room_id,day_of_week) VALUES(%s,%s,%s,%s,%s)',(run,task['offering_id'],task['session_no'],room['room_id'],day))
            for slot in block:
                execute(cn,'INSERT INTO timetable_periods(session_id,slot_id) VALUES(%s,%s)',(sid,slot['slot_id']))
        call(cn,'sp_validate_run',(run,))
        return run,stats
