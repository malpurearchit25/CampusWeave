import sys,json,subprocess,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from db import query
dot=Path(sys.argv[1])
columns=query("SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_KEY FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN (SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='BASE TABLE') ORDER BY TABLE_NAME,ORDINAL_POSITION")
fk=query('SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME,CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL')
unique=query("SELECT TABLE_NAME,INDEX_NAME,GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) cols FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND NON_UNIQUE=0 GROUP BY TABLE_NAME,INDEX_NAME")
tables={}
for c in columns:tables.setdefault(c['TABLE_NAME'],[]).append(c)
(ROOT/'docs/schema_dictionary.json').write_text(json.dumps({'tables':tables,'foreign_keys':fk,'unique_keys':unique},indent=2))
groups={
 'ER_complete':{t for t in tables if not t.startswith('dw_')},
 'ER_overview':{t for t in tables if not t.startswith('dw_')},
 'ER_warehouse':{t for t in tables if t.startswith('dw_')},
 'ER_academic':{'departments','users','faculty','courses','divisions','rooms','time_slots','faculty_courses','faculty_unavailability'},
 'ER_scheduling':{'departments','users','faculty_courses','course_offerings','courses','divisions','timetable_runs','timetable_sessions','timetable_periods','rooms','time_slots','approval_history','scheduling_lock'}}
for name,included in groups.items():
    parts=['digraph ER { graph [rankdir=LR, bgcolor="#ffffff", pad="0.35", nodesep="0.45",ranksep="0.85",splines=polyline]; node [shape=plain,fontname="Arial",fontsize=11]; edge [color="#6481a5",fontname="Arial",fontsize=9,arrowsize=.7];']
    for table,cols in tables.items():
        if table not in included:continue
        label='<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="7" COLOR="#c6d4e5"><TR><TD BGCOLOR="#193b65"><FONT COLOR="white"><B>'+table+'</B></FONT></TD></TR>'
        for c in cols:
            if name=='ER_overview' and c['COLUMN_KEY']!='PRI':continue
            keys=[]
            if c['COLUMN_KEY']=='PRI':keys.append('PK')
            if any(f['TABLE_NAME']==table and f['COLUMN_NAME']==c['COLUMN_NAME'] for f in fk):keys.append('FK')
            if c['COLUMN_KEY']=='UNI':keys.append('UK')
            text=c['COLUMN_NAME']+(' ['+','.join(keys)+']' if keys else '')+(' ?' if c['IS_NULLABLE']=='YES' else '')
            label+='<TR><TD ALIGN="LEFT" BGCOLOR="#f4f7fc">'+html.escape(text)+'</TD></TR>'
        label+='</TABLE>'
        parts.append(f'"{table}" [label=<{label}>];')
    seen=set()
    for f in fk:
        parent,child=f['REFERENCED_TABLE_NAME'],f['TABLE_NAME']
        if parent not in included or child not in included or f['CONSTRAINT_NAME'] in seen:continue
        seen.add(f['CONSTRAINT_NAME'])
        optional=parent=='users' and child=='faculty'
        parts.append(f'"{parent}" -> "{child}" [taillabel="{ "0..1" if optional else "1"}",headlabel="{"0..1" if optional else "0..N"}",label="{f["COLUMN_NAME"] if not (parent=="faculty_courses") else "eligible pair"}"];')
    parts.append('}')
    path=ROOT/'docs'/f'{name}.dot';path.write_text('\n'.join(parts))
    for fmt in ['svg','png']:subprocess.run([str(dot),'-T'+fmt,str(path),'-o',str(path.with_suffix('.'+fmt))],check=True)
architecture='''digraph A { graph [rankdir=TB,bgcolor="white",pad="0.4",nodesep="0.5"]; node [shape=box,style="rounded,filled",fillcolor="#eef3fa",color="#b7c9df",fontname="Arial",fontsize=13,margin=".2,.2"];edge [color="#5478a1",fontname="Arial",fontsize=10]; browser [label="Faculty browser\nJinja HTML / CSS / JavaScript"]; server [label="Waitress + Flask\nSession authentication / CSRF\nAllowlisted forms / escaped templates"]; scheduler [label="Bounded backtracking\nAvailability / workload / labs\nPublished resource reservations"]; database [label="MySQL 8.4 / InnoDB\n15 operational tables + 5 warehouse tables\nProcedures + validation triggers\nLocks / audit / transactions"]; mongo [label="MongoDB 8.0 / authenticated\nFaculty feedback documents\nCRUD / aggregation / indexes"]; mart [label="Dimensional teaching mart\nFour dimensions + period facts\nIdempotent load / OLAP ROLLUP"]; server -> mongo [label="PyMongo"]; database -> mart [label="published snapshot"]; browser -> server [label="HTTP on loopback"];server -> scheduler [label="generate"];server -> database [label="parameterized SQL / CALL"];scheduler -> database [label="atomic persistence"]; }'''
path=ROOT/'docs/architecture.dot';path.write_text(architecture)
for fmt in ['svg','png']:subprocess.run([str(dot),'-T'+fmt,str(path),'-o',str(path.with_suffix('.'+fmt))],check=True)
print('Complete ER, academic/scheduling detail diagrams and architecture rendered.')
