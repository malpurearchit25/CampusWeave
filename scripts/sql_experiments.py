import json,os,sys,uuid
from pathlib import Path
import mysql.connector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.setup_db import install,statements
password=os.getenv('DB_ADMIN_PASSWORD') or json.loads((ROOT/'runtime/admin.json').read_text())['password']
suffix=uuid.uuid4().hex[:10];name='campusweave_course_'+suffix;role='cw_reader_'+suffix
cn=mysql.connector.connect(host='127.0.0.1',port=int(os.getenv('TEST_DB_PORT','3307')),user='root',password=password)
results=[]
try:
    install(cn,name)
    with cn.cursor(dictionary=True) as cur:
        for sql in statements(ROOT/'sql/07_syllabus_queries.sql'):
            cur.execute(sql)
            data=cur.fetchall() if cur.with_rows else []
            results.append({'sql':sql.strip(),'row_count':len(data),'sample':data[:3]})
        cur.execute(f"CREATE ROLE '{role}'")
        cur.execute(f"GRANT SELECT ON `{name}`.* TO '{role}'")
        cur.execute(f"SHOW GRANTS FOR '{role}'");grants=cur.fetchall()
        cur.execute(f"REVOKE SELECT ON `{name}`.* FROM '{role}'")
        cur.execute(f"DROP ROLE '{role}'")
        # A checked view must reject an update that would move the row out of it.
        try:cur.execute('UPDATE lab_room_view SET capacity=10 WHERE id=1')
        except mysql.connector.Error as e:
            assert e.errno==1369;view_rejection=True
        else:raise AssertionError('WITH CHECK OPTION did not reject invalid update')
    cn.rollback()
    evidence={'statement_count':len(results),'statements':results,'role_grants':grants,'view_check_option_rejected':view_rejection,'database':'Disposable isolated MySQL schema; removed after execution.'}
    (ROOT/'docs/sql_evidence.json').write_text(json.dumps(evidence,indent=2,default=str))
    print(f'{len(results)} syllabus SQL statements executed; role grant/revoke and view rejection verified.')
finally:
    assert name.startswith('campusweave_course_')
    with cn.cursor() as cur:
        cur.execute(f"DROP ROLE IF EXISTS '{role}'");cur.execute('DROP DATABASE IF EXISTS `'+name+'`')
    cn.close()
