import json, os, sys, uuid
from pathlib import Path
import pytest
import mysql.connector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.setup_db import install

@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    password=os.getenv('DB_ADMIN_PASSWORD')
    if password is None:password=json.loads((ROOT/'runtime/admin.json').read_text())['password']
    name='campusweave_test_'+uuid.uuid4().hex[:12]
    cn=mysql.connector.connect(host='127.0.0.1',port=int(os.getenv('TEST_DB_PORT','3307')),user='root',password=password)
    install(cn,name)
    for key,value in {'DB_HOST':'127.0.0.1','DB_PORT':os.getenv('TEST_DB_PORT','3307'),'DB_USER':'root','DB_PASSWORD':password,'DB_NAME':name,'FLASK_SECRET_KEY':'isolated-test-secret'}.items():monkeypatch.setenv(key,value)
    yield
    assert name.startswith('campusweave_test_') and len(name)==29
    with cn.cursor() as cur:cur.execute('DROP DATABASE `'+name+'`')
    cn.close()

@pytest.fixture
def client():
    from app import app
    app.config['TESTING']=True
    with app.test_client() as client:
        with client.session_transaction() as s:s.update(uid=1,username='admin',csrf='test-csrf')
        yield client
