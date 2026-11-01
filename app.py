import csv, io, json, os, secrets, time
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, Response
from werkzeug.security import check_password_hash
import mysql.connector
from pymongo.errors import PyMongoError
from bson.errors import InvalidId
from db import ROOT, query, rows, transaction, execute, call, lock_catalog
from scheduler import generate, DAYS
from catalog import CATALOG

app=Flask(__name__)
app.secret_key=os.environ['FLASK_SECRET_KEY']
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=256*1024)
attempts={}

def csrf_token():
    if 'csrf' not in session:session['csrf']=secrets.token_hex(32)
    return session['csrf']
app.jinja_env.globals.update(csrf_token=csrf_token,days=DAYS,catalog=CATALOG)
app.jinja_env.filters['clock']=lambda v: str(v)[:-3].zfill(5)
app.jinja_env.filters['pretty']=lambda v: str(v).replace('_',' ').title() if v is not None else 'Any suitable room'

@app.before_request
def protect():
    if request.method=='POST' and not secrets.compare_digest(str(session.get('csrf','')),str(request.form.get('csrf','!'))):
        abort(400,description='This form expired. Refresh the page and try again.')
    if request.endpoint not in ('login','static','health') and not session.get('uid'):
        return redirect(url_for('login'))

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers['Cache-Control']='no-store'
    return response

def error_message(exc):
    if isinstance(exc,mysql.connector.Error):
        if exc.errno==1644:return exc.msg
        if exc.errno==1062:return 'This record already exists. Use a unique code or assignment.'
        if exc.errno in (1451,1452):return 'This record is linked to other data. Check eligibility and existing timetable references.'
        if exc.errno==3819:return 'A value breaks a database rule. Check positive counts, semester 1–8, sessions 1–6, and room requirements.'
        app.logger.exception('Database operation failed')
        return 'Database operation failed. Check the local server and application log.'
    return str(exc)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        recent=[t for t in attempts.get(request.remote_addr,[]) if time.monotonic()-t<60]
        attempts[request.remote_addr]=recent
        if len(recent)>=5:
            flash('Too many attempts. Wait one minute and try again.','error')
        else:
            found=query('SELECT * FROM users WHERE username=%s AND is_active=1',(request.form.get('username',''),))
            if found and check_password_hash(found[0]['password_hash'],request.form.get('password','')):
                session.clear();session.update(uid=found[0]['user_id'],username=found[0]['username']);return redirect(url_for('home'))
            recent.append(time.monotonic());flash('Username or password is incorrect.','error')
    return render_template('login.html',title='Welcome')

@app.post('/logout')
def logout():session.clear();return redirect(url_for('login'))

@app.get('/health')
def health():
    try:query('SELECT 1');return {'status':'ok','database':'connected'}
    except mysql.connector.Error:return {'status':'unavailable'},503

@app.get('/')
def home():
    counts={table:query('SELECT COUNT(*) n FROM '+table)[0]['n'] for table in ['faculty','courses','divisions','rooms']}
    runs=query('SELECT tr.*,d.department_name,(SELECT COUNT(*) FROM timetable_entries te WHERE te.run_id=tr.run_id) periods FROM timetable_runs tr JOIN departments d USING(department_id) ORDER BY run_id DESC')
    return render_template('home.html',title='Planning studio',counts=counts,runs=runs)

@app.route('/academic/<table>',methods=['GET','POST'])
def academic(table):
    if table not in CATALOG:abort(404)
    meta=CATALOG[table];fields=meta['fields'];pk=meta['pk']
    choices={}
    for f in fields:
        if isinstance(f['choices'],tuple):
            t,k,v=f['choices'];choices[f['name']]=[(r[k],str(r[v])) for r in query(f'SELECT {k},{v} FROM {t} ORDER BY {v}')]
        elif f['choices']:choices[f['name']]=[(v,v.replace('_',' ').title()) for v in f['choices']]
    if request.method=='POST':
        try:
            with transaction() as cn:
                lock_catalog(cn)
                action=request.form.get('action','save');rid=request.form.get('id')
                if action=='delete':
                    if pk:execute(cn,f'DELETE FROM {table} WHERE {pk}=%s',(int(rid),))
                    else:execute(cn,'DELETE FROM faculty_courses WHERE faculty_id=%s AND course_id=%s',(int(request.form['faculty_id']),int(request.form['course_id'])))
                else:
                    values=[]
                    for f in fields:
                        value=request.form.get(f['name'],'').strip()
                        if not value and f['kind']!='optional':raise ValueError(f['label']+' is required.')
                        if len(value)>100:raise ValueError('Keep text fields within 100 characters.')
                        if f['kind']=='number':
                            value=int(value)
                            if not 1<=value<=1000:raise ValueError('Numeric values must be between 1 and 1000.')
                        elif f['name'] in choices and value and value not in [str(k) for k,v in choices[f['name']]]:raise ValueError('Choose an available option.')
                        values.append(value or None)
                    names=[f['name'] for f in fields]
                    if rid and pk:execute(cn,f'UPDATE {table} SET '+','.join(n+'=%s' for n in names)+f' WHERE {pk}=%s',tuple(values)+ (int(rid),))
                    else:execute(cn,f'INSERT INTO {table} ('+','.join(names)+') VALUES('+','.join(['%s']*len(values))+')',tuple(values))
            flash('Record removed.' if action=='delete' else 'Academic data saved.','success')
        except (ValueError,mysql.connector.Error) as e:flash(error_message(e),'error')
        return redirect(url_for('academic',table=table))
    records=query(f'SELECT * FROM {table}')
    edit=next((r for r in records if str(r.get(pk))==request.args.get('edit')),None) if pk else None
    labels={k:{str(i):v for i,v in items} for k,items in choices.items()}
    return render_template('academic.html',title='Academic data',table=table,meta=meta,records=records,choices=choices,labels=labels,edit=edit)

@app.route('/generate',methods=['GET','POST'])
def generate_page():
    if request.method=='POST':
        try:
            run,stats=generate(int(request.form['department']),request.form['year'],int(request.form['semester']),session['uid'])
            flash(f"Draft ready. {stats['sessions']} sessions placed in {stats['seconds']} seconds.",'success')
            return redirect(url_for('timetable',run_id=run))
        except (ValueError,mysql.connector.Error) as e:flash(error_message(e),'error')
    scopes=query('SELECT DISTINCT d.department_id,department_name,academic_year,semester FROM divisions d JOIN departments USING(department_id) ORDER BY department_name,academic_year,semester')
    return render_template('generate.html',title='Create a timetable',scopes=scopes)

def run_data(run_id):
    runs=query('SELECT tr.*,department_name FROM timetable_runs tr JOIN departments USING(department_id) WHERE run_id=%s',(run_id,))
    if not runs:abort(404)
    entries=query('''SELECT te.*,ts.start_time,ts.end_time,c.course_code,c.course_name,c.subject_type,c.course_id,
        f.faculty_name,d.division_id,d.division_name,r.room_code FROM timetable_entries te JOIN time_slots ts USING(slot_id)
        JOIN course_offerings co USING(offering_id) JOIN courses c USING(course_id) JOIN faculty f USING(faculty_id)
        JOIN divisions d USING(division_id) JOIN rooms r USING(room_id) WHERE te.run_id=%s ORDER BY ts.start_time''',(run_id,))
    return runs[0],entries

@app.get('/timetable/<int:run_id>')
def timetable(run_id):
    run,entries=run_data(run_id);issue=None
    if run['status']!='ARCHIVED':
        try:
            with transaction() as cn:call(cn,'sp_validate_run',(run_id,))
        except mysql.connector.Error as e:issue=error_message(e)
    divisions={e['division_id']:e['division_name'] for e in entries}
    selected=request.args.get('division',type=int) or next(iter(divisions),None)
    if selected not in divisions and divisions:abort(404)
    grid={(e['slot_id'],e['day_of_week']):e for e in entries if e['division_id']==selected}
    spans={};covered=set();blocks={}
    for e in entries:
        if e['division_id']==selected:blocks.setdefault((e['offering_id'],e['session_no'],e['day_of_week']),[]).append(e)
    for block in blocks.values():
        block.sort(key=lambda e:e['start_time'])
        if len(block)>1:
            spans[block[0]['slot_id'],block[0]['day_of_week']]=len(block)
            covered.update((e['slot_id'],e['day_of_week']) for e in block[1:])
    audit=query('SELECT ah.*,username FROM approval_history ah JOIN users ON users.user_id=ah.action_by WHERE run_id=%s ORDER BY approval_id',(run_id,))
    return render_template('timetable.html',title='Weekly timetable',run=run,entries=entries,divisions=divisions,selected=selected,grid=grid,spans=spans,covered=covered,slots=query('SELECT * FROM time_slots ORDER BY start_time'),issue=issue,audit=audit)

@app.post('/timetable/<int:run_id>/<action>')
def run_action(run_id,action):
    if action not in ('publish','archive','delete'):abort(404)
    try:
        with transaction() as cn:
            lock_catalog(cn)
            if action=='publish':call(cn,'sp_publish_run',(run_id,session['uid']))
            elif action=='archive':
                execute(cn,'SET @campus_actor=%s',(session['uid'],))
                if not rows(cn,"SELECT run_id FROM timetable_runs WHERE run_id=%s AND status='PUBLISHED'",(run_id,)):raise ValueError('Only a published timetable can be archived.')
                execute(cn,"UPDATE timetable_runs SET status='ARCHIVED' WHERE run_id=%s",(run_id,))
            else:
                if not rows(cn,"SELECT run_id FROM timetable_runs WHERE run_id=%s AND status='DRAFT'",(run_id,)):raise ValueError('Only drafts can be deleted.')
                execute(cn,'DELETE p FROM timetable_periods p JOIN timetable_sessions s USING(session_id) WHERE s.run_id=%s',(run_id,))
                execute(cn,'DELETE FROM timetable_sessions WHERE run_id=%s',(run_id,))
                execute(cn,'DELETE FROM timetable_runs WHERE run_id=%s',(run_id,))
        flash({'publish':'Published. Validation and audit history were saved together.','archive':'Archived. History is retained; resources are available again.','delete':'Draft deleted.'}[action],'success')
        return redirect(url_for('home') if action=='delete' else url_for('timetable',run_id=run_id))
    except (ValueError,mysql.connector.Error) as e:flash(error_message(e),'error');return redirect(url_for('timetable',run_id=run_id))

@app.get('/timetable/<int:run_id>/export.csv')
def export(run_id):
    run,entries=run_data(run_id);output=io.StringIO();writer=csv.writer(output)
    keys=['division_name','day_of_week','start_time','end_time','course_code','course_name','faculty_name','room_code']
    writer.writerow(keys)
    for e in sorted(entries,key=lambda e:(e['division_name'],DAYS.index(e['day_of_week']),e['start_time'])):
        writer.writerow([("'"+str(e[k])) if str(e[k]).startswith(('=','+','-','@')) else str(e[k]) for k in keys])
    return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename=campusweave-{run_id}.csv'})

@app.get('/analytics')
def analytics():
    years=query('SELECT DISTINCT academic_year FROM divisions ORDER BY academic_year DESC')
    year=request.args.get('year') or (years[0]['academic_year'] if years else '')
    faculty=query('''SELECT f.faculty_name,f.max_weekly_hours,COALESCE(x.hours,0) hours FROM faculty f LEFT JOIN
      (SELECT co.faculty_id,COUNT(*) hours FROM timetable_entries te JOIN timetable_runs tr USING(run_id)
      JOIN course_offerings co USING(offering_id) WHERE tr.status='PUBLISHED' AND tr.academic_year=%s GROUP BY co.faculty_id) x USING(faculty_id) ORDER BY hours DESC''',(year,))
    rooms=query('''SELECT r.room_code,r.room_name,COALESCE(x.hours,0) hours FROM rooms r LEFT JOIN
      (SELECT te.room_id,COUNT(*) hours FROM timetable_entries te JOIN timetable_runs tr USING(run_id)
      WHERE tr.status='PUBLISHED' AND tr.academic_year=%s GROUP BY te.room_id) x USING(room_id) WHERE r.is_active=1 ORDER BY hours DESC''',(year,))
    available=query("SELECT COUNT(*)*6 n FROM time_slots WHERE slot_type='TEACHING'")[0]['n']
    return render_template('analytics.html',title='Resource insights',faculty=faculty,rooms=rooms,available=available,years=years,year=year)

@app.route('/lab',methods=['GET','POST'])
def lab():
    result=None
    if request.method=='POST':
        marker='LAB_'+secrets.token_hex(8)
        with transaction() as cn:
            lock_catalog(cn)
            execute(cn,'INSERT INTO departments(department_name) VALUES(%s)',(marker,))
            before=rows(cn,'SELECT COUNT(*) n FROM departments WHERE department_name=%s',(marker,))[0]['n']
            execute(cn,'SAVEPOINT before_second_insert')
            execute(cn,'INSERT INTO departments(department_name) VALUES(%s)',(marker+'_SECOND',))
            execute(cn,'ROLLBACK TO SAVEPOINT before_second_insert')
            after_savepoint=rows(cn,'SELECT COUNT(*) n FROM departments WHERE department_name LIKE %s',(marker+'%',))[0]['n']
            cn.rollback()
            after=query('SELECT COUNT(*) n FROM departments WHERE department_name LIKE %s',(marker+'%',))[0]['n']
            result=dict(before=before,savepoint=after_savepoint,after=after)
    routines=query('SELECT ROUTINE_NAME,ROUTINE_TYPE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE()')
    with transaction() as cn:
        with cn.cursor(dictionary=True) as cur:
            cur.execute('CALL sp_trigger_inventory()')
            triggers=cur.fetchall()
            cur.nextset()
    evidence=ROOT/'docs/evidence.json'
    return render_template('lab.html',title='DBMS demonstration lab',routines=routines,triggers=triggers,result=result,evidence=json.loads(evidence.read_text()) if evidence.exists() else {})

@app.get('/guide')
def guide():return render_template('guide.html',title='Project field guide')

@app.route('/lab/mongodb',methods=['GET','POST'])
def mongo_lab():
    from mongo_store import save_feedback,feedback_list,delete_feedback
    if request.method=='POST':
        try:
            if request.form.get('action')=='delete':delete_feedback(request.form['id'])
            else:save_feedback(request.form,session['username'])
            flash('Faculty feedback saved in MongoDB.' if request.form.get('action')!='delete' else 'Feedback removed.','success')
        except (ValueError,InvalidId) as e:flash(str(e),'error')
        except PyMongoError:flash('MongoDB is unavailable. Start the local database and try again.','error')
        return redirect(url_for('mongo_lab'))
    try:notes,summary=feedback_list();available=True
    except PyMongoError:notes,summary,available=[],[],False
    edit=next((r for r in notes if str(r['_id'])==request.args.get('edit')),None)
    evidence=ROOT/'docs/mongo_evidence.json'
    return render_template('mongo.html',title='Faculty feedback · MongoDB',notes=notes,summary=summary,available=available,edit=edit,evidence=json.loads(evidence.read_text()) if evidence.exists() else {})

@app.get('/lab/theory')
def theory_lab():
    from syllabus_lab import run_theory_experiments
    return render_template('theory.html',title='Syllabus experiments',evidence=run_theory_experiments())

@app.route('/lab/warehouse',methods=['GET','POST'])
def warehouse_lab():
    from warehouse import load_mart,olap
    if request.method=='POST':
        count=load_mart();flash(f'Warehouse refreshed. {count} historical occupied periods retained.','success')
        return redirect(url_for('warehouse_lab'))
    return render_template('warehouse.html',title='Academic data warehouse',records=olap())

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def error(e):return render_template('error.html',title='Let’s get you back',message=getattr(e,'description','Something went wrong.')),getattr(e,'code',500)

if __name__=='__main__':
    from waitress import serve
    serve(app,host='127.0.0.1',port=int(os.getenv('PORT','5050')))
