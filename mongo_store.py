"""Non-relational connectivity: flexible faculty feedback documents, separate from SQL scheduling."""
import os
from datetime import datetime,timezone
from contextlib import contextmanager
from pymongo import MongoClient,ASCENDING
from bson import ObjectId

@contextmanager
def collection():
    with MongoClient(os.environ.get('MONGO_URI','mongodb://127.0.0.1:27018'),serverSelectionTimeoutMS=3000) as client:
        col=client[os.getenv('MONGO_DB','campusweave')].faculty_feedback
        col.create_index([('course',ASCENDING),('rating',ASCENDING)],name='course_rating')
        yield col

def save_feedback(data,actor):
    rating=int(data.get('rating','0'))
    if rating not in range(1,6):raise ValueError('Choose a rating from 1 to 5.')
    note=data.get('note','').strip();course=data.get('course','').strip()
    if not course or not note or len(note)>1000 or len(course)>100:raise ValueError('Enter a course and a note up to 1,000 characters.')
    doc={'course':course,'rating':rating,'note':note,'tags':[x.strip()[:30] for x in data.get('tags','').split(',') if x.strip()][:8],
         'author':actor,'updated_at':datetime.now(timezone.utc)}
    with collection() as col:
        if data.get('id'):col.update_one({'_id':ObjectId(data['id'])},{'$set':doc})
        else:doc['created_at']=doc['updated_at'];col.insert_one(doc)

def feedback_list():
    with collection() as col:
        return list(col.find().sort('updated_at',-1)),list(col.aggregate([{'$group':{'_id':'$course','average':{'$avg':'$rating'},'count':{'$sum':1}}},{'$sort':{'_id':1}}]))

def delete_feedback(oid):
    with collection() as col:col.delete_one({'_id':ObjectId(oid)})
