"""Small, explicit DB-API layer: parameter binding and one transaction per unit of work."""
import os
from contextlib import contextmanager
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')

def connect(database=None):
    return mysql.connector.connect(host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3307')), user=os.getenv('DB_USER', 'campus_app'),
        password=os.getenv('DB_PASSWORD', ''), database=database or os.getenv('DB_NAME', 'campusweave'),
        autocommit=False, connection_timeout=10)

@contextmanager
def transaction():
    cn = connect()
    try:
        yield cn
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()

def rows(cn, sql, params=()):
    with cn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def query(sql, params=()):
    with transaction() as cn:
        return rows(cn, sql, params)

def execute(cn, sql, params=()):
    with cn.cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid

def call(cn, name, args):
    with cn.cursor() as cur:
        result = cur.callproc(name, args)
        # These procedures intentionally return no result sets (only SIGNAL on failure).
        return result

def lock_catalog(cn):
    # All application writes share this lock; publication repeats validation under it.
    rows(cn, 'SELECT lock_id FROM scheduling_lock WHERE lock_id=1 FOR UPDATE')
