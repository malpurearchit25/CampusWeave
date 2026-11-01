"""Initialize a new, isolated database. Refuses to overwrite any existing schema."""
import sys, os, secrets, json, argparse
from pathlib import Path
import mysql.connector
from werkzeug.security import generate_password_hash

ROOT=Path(__file__).resolve().parents[1]
def statements(path):
    delimiter=';'; buf=''
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip().upper().startswith('DELIMITER '):
            delimiter=line.strip().split()[1];continue
        if line.lstrip().startswith('--'):continue
        buf+=line+'\n'
        if buf.rstrip().endswith(delimiter):
            yield buf.rstrip()[:-len(delimiter)];buf=''
    if buf.strip():raise ValueError('Unterminated SQL')

def install(cn,name):
    if not name.replace('_','').isalnum():raise ValueError('Invalid database name')
    with cn.cursor() as cur:
        cur.execute('CREATE DATABASE `'+name+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        cur.execute('USE `'+name+'`')
        for filename in ['01_schema.sql','02_routines.sql','03_catalog_guards.sql','05_warehouse.sql','06_teaching_objects.sql']:
            for sql in statements(ROOT/'sql'/filename):cur.execute(sql)
        cur.execute('UPDATE users SET password_hash=%s WHERE username=%s',(generate_password_hash('CampusDemo!2026'),'admin'))
    cn.commit()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bootstrap-local',action='store_true');p.add_argument('--database',default='campusweave');a=p.parse_args()
    if a.bootstrap_local:
        cn=mysql.connector.connect(host='127.0.0.1',port=3307,user='root',password='')
        admin=secrets.token_urlsafe(32);password=secrets.token_urlsafe(32)
        with cn.cursor() as cur:
            cur.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s",(admin,))
            cur.execute("CREATE USER 'campus_app'@'127.0.0.1' IDENTIFIED BY %s",(password,))
        (ROOT/'runtime/admin.json').write_text(json.dumps({'password':admin}))
        install(cn,a.database)
        with cn.cursor() as cur:cur.execute('GRANT SELECT,INSERT,UPDATE,DELETE,EXECUTE ON `'+a.database+"`.* TO 'campus_app'@'127.0.0.1'")
        (ROOT/'.env').write_text(f'DB_HOST=127.0.0.1\nDB_PORT=3307\nDB_USER=campus_app\nDB_PASSWORD={password}\nDB_NAME={a.database}\nFLASK_SECRET_KEY={secrets.token_urlsafe(48)}\nPORT=5050\n')
        cn.close();print('Local MySQL secured; application schema initialized. Login: admin / CampusDemo!2026')
    else:
        cn=mysql.connector.connect(host=os.getenv('DB_HOST','127.0.0.1'),port=int(os.getenv('DB_PORT','3307')),user=os.getenv('DB_ADMIN','root'),password=os.environ['DB_ADMIN_PASSWORD'])
        install(cn,a.database);cn.close();print('Created new database '+a.database)
