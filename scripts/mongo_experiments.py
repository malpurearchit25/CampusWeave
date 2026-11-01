"""At least ten actual MongoDB operations, aggregation, indexing and legacy MapReduce."""
import json,os,uuid
from pathlib import Path
from datetime import datetime,timezone
from pymongo import MongoClient
from bson.code import Code
ROOT=Path(__file__).resolve().parents[1]
password=os.getenv('MONGO_ADMIN_PASSWORD') or json.loads((ROOT/'runtime/mongo-admin.json').read_text())['password']
name='campusweave_lab_'+uuid.uuid4().hex[:10]
with MongoClient(f'mongodb://campus_admin:{password}@127.0.0.1:27018/admin') as client:
    db=client[name];col=db.feedback;results={}
    try:
        docs=[{'course':course,'rating':rating,'tags':tags,'note':note,'created_at':datetime.now(timezone.utc)} for course,rating,tags,note in [
          ('DBMS',5,['theory','morning'],'Clear morning periods'),('DBMS',4,['theory'],'Good spacing'),('DBMSL',5,['lab'],'Consecutive lab works well'),('DSA',3,['theory'],'Prefer an earlier period'),('DSA',4,['theory','morning'],'Balanced workload'),('PYLAB',4,['lab'],'Suitable computer lab')]]
        results['01_insert_many']=len(col.insert_many(docs).inserted_ids)
        results['02_find_all']=col.count_documents({})
        results['03_equality']=len(list(col.find({'course':'DBMS'})))
        results['04_comparison']=len(list(col.find({'rating':{'$gte':4}})))
        results['05_projection']=list(col.find({'course':'DBMS'},{'_id':0,'course':1,'rating':1}))
        results['06_array_membership']=col.count_documents({'tags':'lab'})
        results['07_sort_limit']=[r['rating'] for r in col.find().sort('rating',-1).limit(2)]
        results['08_update_one']=col.update_one({'course':'DSA','rating':3},{'$set':{'rating':4}}).modified_count
        results['09_update_many']=col.update_many({'tags':'lab'},{'$addToSet':{'tags':'practical'}}).modified_count
        temp=col.insert_one({'course':'TEMP','rating':1}).inserted_id
        results['10_delete_one']=col.delete_one({'_id':temp}).deleted_count
        results['11_distinct']=sorted(col.distinct('course'))
        results['12_aggregation']=list(col.aggregate([{'$group':{'_id':'$course','average':{'$avg':'$rating'},'total':{'$sum':'$rating'},'count':{'$sum':1}}},{'$sort':{'_id':1}}]))
        results['13_create_index']=col.create_index([('course',1),('rating',1)],name='course_rating')
        plan=col.find({'course':'DBMS','rating':{'$gte':4}}).hint('course_rating').explain()
        results['14_index_explain']=plan['queryPlanner']['winningPlan']
        results['15_regex']=col.count_documents({'course':{'$regex':'^DB'}})
        results['16_legacy_mapreduce']=db.command('mapReduce','feedback',map=Code('function(){emit(this.course,this.rating);}'),reduce=Code('function(key,values){return Array.sum(values);}'),out={'inline':1})['results']
        expected={r['_id']:r['total'] for r in results['12_aggregation']}
        assert {r['_id']:r['value'] for r in results['16_legacy_mapreduce']}==expected
        results['mapreduce_matches_aggregation']=True
        results['mongodb_version']=client.server_info()['version']
        results['scope']='Executed in an isolated disposable database; legacy MapReduce is deprecated and included only for syllabus compatibility.'
        (ROOT/'docs/mongo_evidence.json').write_text(json.dumps(results,indent=2,default=str))
        print('16 MongoDB operations passed; actual MapReduce output equals aggregation totals.')
    finally:
        assert name.startswith('campusweave_lab_');client.drop_database(name)
