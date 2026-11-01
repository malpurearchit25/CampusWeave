"""Reproducible EXPLAIN comparison in a uniquely named disposable database."""
import json, os, sys, uuid, time, statistics
from pathlib import Path
import mysql.connector
ROOT=Path(__file__).resolve().parents[1]
password=os.getenv('DB_ADMIN_PASSWORD') or json.loads((ROOT/'runtime/admin.json').read_text())['password']
name='campusweave_bench_'+uuid.uuid4().hex[:12]
cn=mysql.connector.connect(host='127.0.0.1',port=int(os.getenv('TEST_DB_PORT','3307')),user='root',password=password)
try:
    cur=cn.cursor(dictionary=True)
    cur.execute('CREATE DATABASE `'+name+'`');cur.execute('USE `'+name+'`')
    cur.execute('CREATE TABLE entries(entry_id INT PRIMARY KEY,run_id INT,day_of_week INT,slot_id INT,payload VARCHAR(100))')
    n=60000
    for offset in range(0,n,1000):
        cur.executemany('INSERT INTO entries VALUES(%s,%s,%s,%s,%s)',[(i+1,i//60+1,i%6,i//6%10,'controlled benchmark row') for i in range(offset,offset+1000)])
    cn.commit()
    sql='SELECT * FROM entries WHERE run_id=501 AND day_of_week=2 AND slot_id=3'
    def sample():
        cur.execute('EXPLAIN '+sql);plan=cur.fetchall()
        samples=[]
        for _ in range(7):
            started=time.perf_counter();cur.execute(sql);result=cur.fetchall();samples.append((time.perf_counter()-started)*1000)
        return plan,round(statistics.median(samples),3),len(result)
    before,bt,bc=sample()
    cur.execute('CREATE INDEX idx_run_day_slot ON entries(run_id,day_of_week,slot_id)')
    cur.execute('ANALYZE TABLE entries');cur.fetchall()
    after,at,ac=sample()
    assert bc==ac==1
    result={'mysql_version':cn.server_info,'benchmark_rows':n,'query':sql,'before_access':before[0]['type'],'after_access':after[0]['type'],'before_rows':before[0]['rows'],'after_rows':after[0]['rows'],'before_median_ms':bt,'after_median_ms':at,'samples_per_case':7,'result_count':ac,'before_plan':before,'after_plan':after,'scope':'Isolated synthetic table; not a production performance claim.'}
    (ROOT/'docs/evidence.json').write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps({k:v for k,v in result.items() if 'plan' not in k},indent=2))
finally:
    assert name.startswith('campusweave_bench_')
    with cn.cursor() as cleanup:cleanup.execute('DROP DATABASE `'+name+'`')
    cn.close()
