import secrets,json
from pathlib import Path
from pymongo import MongoClient
ROOT=Path(__file__).resolve().parents[1]
password=secrets.token_urlsafe(32)
# MongoDB localhost exception allows creation of the first administrator only.
with MongoClient('mongodb://127.0.0.1:27018',serverSelectionTimeoutMS=5000) as client:
    client.admin.command('createUser','campus_admin',pwd=password,roles=[{'role':'root','db':'admin'}])
(ROOT/'runtime/mongo-admin.json').write_text(json.dumps({'password':password}))
app_password=secrets.token_urlsafe(32)
with MongoClient(f'mongodb://campus_admin:{password}@127.0.0.1:27018/admin') as client:
    client.campusweave.command('createUser','campus_mongo',pwd=app_password,roles=[{'role':'readWrite','db':'campusweave'}])
with (ROOT/'.env').open('a') as f:f.write(f'MONGO_URI=mongodb://campus_mongo:{app_password}@127.0.0.1:27018/campusweave\nMONGO_DB=campusweave\n')
print('MongoDB authentication configured. Application has database-scoped read/write privileges.')
