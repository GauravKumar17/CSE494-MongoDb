import os
from datetime import timedelta
from unittest.mock import patch
import pytest
import mongomock
from django.test import Client
from django.core.management import call_command
from django.contrib.auth.hashers import make_password
from pymongo.errors import DuplicateKeyError, OperationFailure
from market.db import db, indexes
from market.auth import now
from market.management.commands.seed_demo import DEMO_PASSWORD

@pytest.fixture(autouse=True)
def isolated_db(settings):
    settings.DEBUG=True;settings.ALLOWED_HOSTS=['testserver','localhost'];settings.MONGODB_DATABASE='neighbourly_test_automation'
    if os.getenv('REAL_MONGO_TEST')=='1':
        from market.db import client
        d=db();d.command('ping');client().drop_database(settings.MONGODB_DATABASE)
        call_command('setup_database',verbosity=0)
        yield d
        client().drop_database(settings.MONGODB_DATABASE)
    else:
        mock=mongomock.MongoClient(tz_aware=True)
        with patch('market.db.client',return_value=mock):
            indexes();yield db()

@pytest.fixture
def seeded(isolated_db):
    call_command('seed_demo',verbosity=0);return isolated_db

def sign_in(email):
    c=Client();response=c.post('/login/',{'email':email,'password':DEMO_PASSWORD});assert response.status_code==302;return c

def request_visit(c,w,**extra):
    return c.post(f'/workers/{w["_id"]}/book/',{'date':(now()+timedelta(days=2)).date().isoformat(),'hour':'10','address':'Synthetic test address','description':'Please repair the loose kitchen switch.',**extra})

def test_public_and_role_pages(seeded):
    c=Client()
    for path in ['/','/services/','/signup/','/login/','/community/','/how-it-works/']:
        assert c.get(path).status_code==200
    w=seeded.worker_profiles.find_one({})
    assert c.get(f'/workers/{w["_id"]}/').status_code==200
    assert c.get('/admin/').status_code==302
    assert sign_in('customer@example.com').get('/admin/').status_code==403
    assert sign_in('admin@example.com').get('/admin/').status_code==200
    wc=sign_in('worker@example.com')
    assert wc.get('/dashboard/').status_code==200
    assert wc.get('/profile/').status_code==200

def test_signup_hash_and_role_allowlist(seeded):
    c=Client();data={'name':'A New Neighbour','email':'NEW@example.com','password':'SecureLearning!2026','confirm_password':'SecureLearning!2026','role':'customer'}
    assert c.post('/signup/',data).status_code==302
    u=seeded.users.find_one({'email':'new@example.com'});assert u and u['password_hash']!=data['password']
    assert len(c.cookies['neighbourly_session'].value)>35
    c2=Client();data.update(email='hack@example.com',role='admin')
    assert c2.post('/signup/',data).status_code==200
    assert not seeded.users.find_one({'email':'hack@example.com'})

def test_booking_conflict_private_address_and_lifecycle(seeded):
    customer=sign_in('customer@example.com');worker=sign_in('worker@example.com');w=seeded.worker_profiles.find_one({'name':'Ravi Kumar'})
    assert request_visit(customer,w).status_code==302
    b=seeded.bookings.find_one({});path=f'/bookings/{b["_id"]}/'
    assert request_visit(customer,w).status_code==200
    assert seeded.bookings.count_documents({})==1
    stranger=Client();stranger.post('/signup/',{'name':'Stranger','email':'stranger@example.com','password':'SecureLearning!2026','confirm_password':'SecureLearning!2026','role':'customer'})
    denied=stranger.get(path);assert denied.status_code==404;assert b'Synthetic test address' not in denied.content
    assert customer.post(path+'action/',{'action':'accept'}).status_code==409
    assert customer.post(path+'review/',{'rating':'5','comment':'A very helpful local service.'}).status_code==409
    for actor,action in [(worker,'accept'),(worker,'start'),(worker,'finish'),(customer,'complete')]:assert actor.post(path+'action/',{'action':action}).status_code==302
    assert seeded.bookings.find_one({'_id':b['_id']})['status']=='completed'
    for _ in range(2):assert customer.post(path+'review/',{'rating':'5','comment':'A very helpful local service.'}).status_code==302
    assert seeded.reviews.count_documents({})==1
    assert '5.0' in customer.get('/services/').content.decode()

def test_cancel_releases_slot_and_logout_revokes(seeded):
    c=sign_in('customer@example.com');w=seeded.worker_profiles.find_one({});request_visit(c,w);b=seeded.bookings.find_one({})
    assert c.post(f'/bookings/{b["_id"]}/action/',{'action':'cancel'}).status_code==302
    assert request_visit(c,w).status_code==302
    token=c.cookies['neighbourly_session'].value
    assert c.post('/logout/').status_code==302
    replay=Client();replay.cookies['neighbourly_session']=token
    assert replay.get('/dashboard/').status_code==302

def test_profile_requires_approval_and_admin_can_approve(seeded):
    w=sign_in('worker@example.com')
    assert w.post('/profile/',{'category':'electrical','locality':'Phagwara','bio':'Careful service and honest communication for every visit.','experience':8,'rate':450,'skills':'Switches, Fans','available':'on'}).status_code==302
    row=seeded.worker_profiles.find_one({'name':'Ravi Kumar'});assert row['approved'] is False
    assert b'Ravi Kumar' not in Client().get('/services/').content
    assert w.post(f'/admin/workers/{row["_id"]}/',{'action':'approve'}).status_code==403
    assert sign_in('admin@example.com').post(f'/admin/workers/{row["_id"]}/',{'action':'approve'}).status_code==302
    assert b'Ravi Kumar' in Client().get('/services/').content

def test_csrf_mandatory(seeded):
    c=Client(enforce_csrf_checks=True)
    assert c.post('/login/',{'email':'customer@example.com','password':DEMO_PASSWORD}).status_code==403
    assert c.post('/logout/').status_code==403

def test_invalid_booking_form_and_safe_search(seeded):
    c=sign_in('customer@example.com');w=seeded.worker_profiles.find_one({})
    assert request_visit(c,w,date='2000-01-01',hour='25').status_code==200
    assert seeded.bookings.count_documents({})==0
    assert Client().get('/workers/not-an-objectid/').status_code==404
    assert b'providers found' in Client().get('/services/',{'locality':'.*'}).content
    assert b'No matches' in Client().get('/services/',{'locality':'.*'}).content

def test_login_rate_limit(seeded):
    c=Client()
    for _ in range(31):response=c.post('/login/',{'email':'customer@example.com','password':'incorrect'})
    assert b'Too many attempts' in response.content

@pytest.mark.skipif(os.getenv('REAL_MONGO_TEST')!='1',reason='Requires a real MongoDB server')
def test_real_database_validation_and_concurrent_slot_index(seeded):
    from concurrent.futures import ThreadPoolExecutor
    from bson import ObjectId
    bad={'booking_id':ObjectId(),'customer_id':ObjectId(),'worker_id':ObjectId(),'rating':6,'comment':'Invalid review'}
    with pytest.raises(OperationFailure):seeded.reviews.insert_one(bad)
    w=seeded.worker_profiles.find_one({})
    b={'customer_id':ObjectId(),'worker_id':w['_id'],'status':'requested','active':True,'slot_key':'2099-01-01 10:00','price_paise':39900}
    def insert(i):
        try:seeded.bookings.insert_one(dict(b));return True
        except DuplicateKeyError:return False
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(insert,range(8)))
    assert sum(results)==1

def test_auth_failures_and_invalid_review(seeded):
    c=Client()
    assert b'incorrect' in c.post('/login/',{'email':'nobody@example.com','password':'wrong'}).content
    assert not c.cookies.get('neighbourly_session')
    data={'name':'Short Password','email':'short@example.com','password':'123','confirm_password':'123','role':'customer'}
    assert c.post('/signup/',data).status_code==200
    assert not seeded.users.find_one({'email':'short@example.com'})
    admin=sign_in('admin@example.com')
    w=seeded.worker_profiles.find_one({});customer=sign_in('customer@example.com');request_visit(customer,w)
    b=seeded.bookings.find_one({})
    seeded.bookings.update_one({'_id':b['_id']},{'$set':{'status':'completed','active':False}})
    assert customer.post(f'/bookings/{b["_id"]}/review/',{'rating':'6','comment':'A synthetic test review.'}).status_code==400
    assert seeded.reviews.count_documents({})==0
    assert admin.get('/admin/').status_code==200
    assert b'Electrical' in admin.get('/admin/').content
