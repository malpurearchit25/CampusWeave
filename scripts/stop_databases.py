import json
from pathlib import Path
import mysql.connector
from pymongo import MongoClient
from pymongo.errors import AutoReconnect,ConnectionFailure
ROOT=Path(__file__).resolve().parents[1]
try:
    secret=json.loads((ROOT/'runtime/admin.json').read_text())['password']
    with mysql.connector.connect(host='127.0.0.1',port=3307,user='root',password=secret) as cn:
        with cn.cursor() as cur:cur.execute('SHUTDOWN')
except (mysql.connector.Error,FileNotFoundError):pass
try:
    secret=json.loads((ROOT/'runtime/mongo-admin.json').read_text())['password']
    with MongoClient(f'mongodb://campus_admin:{secret}@127.0.0.1:27018/admin',serverSelectionTimeoutMS=2000) as client:client.admin.command('shutdown')
except (AutoReconnect,ConnectionFailure,FileNotFoundError):pass
