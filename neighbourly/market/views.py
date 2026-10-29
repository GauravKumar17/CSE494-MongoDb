from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from bson.errors import InvalidId
from django.shortcuts import render, redirect
from django.http import Http404
from django.views.decorators.http import require_POST
from django.contrib.auth.hashers import make_password, check_password
from django.middleware.csrf import rotate_token
from pymongo.errors import DuplicateKeyError
from market.db import db
from market.auth import required, establish, throttle, digest, COOKIE, now
from market.forms import SignupForm, LoginForm, ProfileForm, BookingForm, ReviewForm
from market.data import CATEGORY_MAP

def oid(value):
    try: return ObjectId(value)
    except (InvalidId, TypeError): raise Http404

def decorate(w):
    w=dict(w); w['id']=str(w['_id']); w['price']=w.get('rate_paise',0)//100
    w['category_name']=CATEGORY_MAP.get(w.get('category'),{}).get('name','Service')
    w['initials']=''.join(x[0] for x in w.get('name','Local Worker').split()[:2]).upper()
    return w

def workers(query, limit=100):
    items=[decorate(w) for w in db().worker_profiles.find(query).sort([('created_at',-1)]).limit(limit)]
    ids=[w['_id'] for w in items]
    ratings={r['_id']: r for r in db().reviews.aggregate([{'$match': {'worker_id': {'$in': ids}}}, {'$group': {'_id': '$worker_id', 'average': {'$avg':'$rating'}, 'count':{'$sum':1}}}])}
    for w in items:
        r=ratings.get(w['_id'],{});w['rating']=round(r.get('average',0),1);w['review_count']=r.get('count',0)
    return items

def home(request):
    return render(request,'home.html',{'featured':workers({'approved':True,'available':True},3)})

def services(request):
    category=request.GET.get('category',''); locality=request.GET.get('locality','').strip()[:70]
    query={'approved':True,'available':True}
    if category in CATEGORY_MAP: query['category']=category
    if locality: query['locality']={'$regex': __import__('re').escape(locality), '$options':'i'}
    return render(request,'services.html',{'workers':workers(query), 'selected':category,'locality':locality})

def get_worker(worker_id, public=True):
    q={'_id':oid(worker_id)}
    if public: q['approved']=True
    w=db().worker_profiles.find_one(q)
    if not w: raise Http404
    return decorate(w)

def worker_detail(request,worker_id):
    w=get_worker(worker_id)
    reviews=list(db().reviews.find({'worker_id':w['_id']}).sort('created_at',-1).limit(10))
    return render(request,'worker.html',{'worker':w,'reviews':reviews})

def signup(request):
    if request.account:return redirect('dashboard')
    form=SignupForm(request.POST or None)
    if request.method=='POST':
        if throttle(request):form.add_error(None,'Too many attempts. Please try again in 15 minutes.')
        elif form.is_valid():
            c=form.cleaned_data
            try:
                user={'name':c['name'],'email':c['email'].lower(),'role':c['role'],'password_hash':make_password(c['password']),'active':True,'created_at':now()}
                user['_id']=db().users.insert_one(user).inserted_id
            except DuplicateKeyError:form.add_error('email','An account with this email already exists.')
            else:
                rotate_token(request)
                return establish(redirect('profile' if c['role']=='worker' else 'dashboard'),user,request)
    return render(request,'auth.html',{'form':form,'signup':True})

def login(request):
    if request.account:return redirect('dashboard')
    form=LoginForm(request.POST or None)
    if request.method=='POST':
        if throttle(request):form.add_error(None,'Too many attempts. Please try again in 15 minutes.')
        elif form.is_valid():
            u=db().users.find_one({'email':form.cleaned_data['email'].lower(),'active':True})
            valid=check_password(form.cleaned_data['password'], u['password_hash'] if u else DUMMY_HASH)
            if u and valid:
                rotate_token(request);return establish(redirect('admin' if u['role']=='admin' else 'dashboard'),u,request)
            form.add_error(None,'The email or password is incorrect.')
    return render(request,'auth.html',{'form':form,'signup':False})
DUMMY_HASH=make_password('not-a-real-account-password')

@require_POST
def logout(request):
    token=request.COOKIES.get(COOKIE)
    if token:db().sessions.delete_one({'token_hash':digest(token)})
    response=redirect('home');response.delete_cookie(COOKIE);return response

@required('worker')
def profile(request):
    w=db().worker_profiles.find_one({'user_id':request.account['_id']})
    initial=dict(w or {})
    if w:initial['rate']=w['rate_paise']//100;initial['skills']=', '.join(w['skills'])
    form=ProfileForm(request.POST or None,initial=initial)
    if request.method=='POST' and form.is_valid():
        c=form.cleaned_data
        values={k:c[k] for k in ['category','locality','bio','experience','available']}
        values.update(name=request.account['name'],rate_paise=c['rate']*100,skills=[x.strip() for x in c['skills'].split(',') if x.strip()][:8],approved=False)
        db().worker_profiles.update_one({'user_id':request.account['_id']},{'$set':values,'$setOnInsert':{'created_at':now()}},upsert=True)
        return redirect('/dashboard/?saved=1')
    return render(request,'profile.html',{'form':form,'worker':w})

@required('customer')
def book(request,worker_id):
    w=get_worker(worker_id)
    if not w['available']:return render(request,'error.html',{'title':'Taking a little break','description':'This worker is not accepting new bookings.'},status=409)
    form=BookingForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        c=form.cleaned_data;slot=f"{c['date'].isoformat()} {int(c['hour']):02d}:00"
        data={'worker_id':w['_id'],'customer_id':request.account['_id'],'worker_name':w['name'],'customer_name':request.account['name'],'category':w['category'],'locality':w['locality'],'slot_key':slot,'appointment':datetime(c['date'].year,c['date'].month,c['date'].day,int(c['hour']),tzinfo=ZoneInfo('Asia/Kolkata')),'description':c['description'],'address':c['address'],'community':c['community'],'price_paise':w['rate_paise'],'status':'requested','active':True,'created_at':now()}
        try:bid=db().bookings.insert_one(data).inserted_id
        except DuplicateKeyError:form.add_error('hour','This visit slot has just been booked. Please choose another.')
        else:return redirect('booking_detail',booking_id=str(bid))
    return render(request,'book.html',{'form':form,'worker':w})

def own_booking(request,booking_id):
    b=db().bookings.find_one({'_id':oid(booking_id)})
    if not b:raise Http404
    w=db().worker_profiles.find_one({'user_id':request.account['_id']}) if request.account['role']=='worker' else None
    if not (b['customer_id']==request.account['_id'] or (w and b['worker_id']==w['_id']) or request.account['role']=='admin'):raise Http404
    b['id']=str(b['_id']);b['price']=b['price_paise']//100
    b['status_label']=b['status'].replace('_',' ').title()
    return b

@required()
def dashboard(request):
    if request.account['role']=='admin':return redirect('admin')
    w=db().worker_profiles.find_one({'user_id':request.account['_id']}) if request.account['role']=='worker' else None
    query={'worker_id':w['_id']} if w else {'customer_id':request.account['_id']}
    bookings=list(db().bookings.find(query).sort('created_at',-1).limit(100))
    for b in bookings:b['id']=str(b['_id']);b['price']=b['price_paise']//100;b['status_label']=b['status'].replace('_',' ').title()
    return render(request,'dashboard.html',{'bookings':bookings,'worker':w,'total':db().bookings.count_documents(query),'completed':db().bookings.count_documents({**query,'status':'completed'}),'pending':db().bookings.count_documents({**query,'status':{'$in':['requested','confirmed','in_progress','completion_pending']}})})

@required()
def booking_detail(request,booking_id):
    b=own_booking(request,booking_id)
    return render(request,'booking.html',{'booking':b,'review_form':ReviewForm(),'existing_review':db().reviews.find_one({'booking_id':b['_id']})})

@require_POST
@required('customer','worker')
def booking_action(request,booking_id):
    b=own_booking(request,booking_id);action=request.POST.get('action');role=request.account['role']
    transitions={('worker','accept'):('requested','confirmed'),('worker','decline'):('requested','declined'),('worker','start'):('confirmed','in_progress'),('worker','finish'):('in_progress','completion_pending'),('customer','complete'):('completion_pending','completed')}
    target=transitions.get((role,action))
    if action=='cancel' and role=='customer' and b['status'] in ['requested','confirmed']:target=(b['status'],'cancelled')
    if not target or b['status']!=target[0]:return render(request,'error.html',{'title':'This booking has moved on','description':'Refresh the booking and choose an available action.'},status=409)
    update={'status':target[1],'updated_at':now()}
    if target[1] in ['declined','cancelled','completed']:update['active']=False
    if target[1]=='completed':update['completed_at']=now()
    result=db().bookings.update_one({'_id':b['_id'],'status':target[0]},{'$set':update})
    if not result.matched_count:return render(request,'error.html',{'title':'Booking already updated','description':'Please refresh to see its current status.'},status=409)
    return redirect('booking_detail',booking_id=booking_id)

@require_POST
@required('customer')
def review(request,booking_id):
    b=own_booking(request,booking_id)
    if b['status']!='completed':return render(request,'error.html',{'title':'Finish the visit first','description':'Reviews open after you confirm completion.'},status=409)
    form=ReviewForm(request.POST)
    if form.is_valid():
        try:db().reviews.insert_one({'booking_id':b['_id'],'worker_id':b['worker_id'],'customer_id':request.account['_id'],'customer_name':request.account['name'],'rating':int(form.cleaned_data['rating']),'comment':form.cleaned_data['comment'],'created_at':now()})
        except DuplicateKeyError:pass
        return redirect('booking_detail',booking_id=booking_id)
    return render(request,'booking.html',{'booking':b,'review_form':form,'existing_review':None},status=400)

def community(request):
    count=db().bookings.count_documents({'community':True,'status':'completed'})
    return render(request,'community.html',{'community_count':count})
def how_it_works(request):return render(request,'how.html')

@required('admin')
def admin(request):
    pending=workers({'approved':False},100)
    recent=list(db().bookings.find({}, {'address':0,'description':0}).sort('created_at',-1).limit(8))
    demand=list(db().bookings.aggregate([{'$group':{'_id':'$category','count':{'$sum':1}}},{'$sort':{'count':-1}}]))
    for x in demand:x['name']=CATEGORY_MAP.get(x['_id'],{}).get('name',x['_id'])
    return render(request,'admin.html',{'pending_workers':pending,'recent':recent,'demand':demand,'users_count':db().users.count_documents({}),'workers_count':db().worker_profiles.count_documents({'approved':True}),'bookings_count':db().bookings.count_documents({}),'completed_count':db().bookings.count_documents({'status':'completed'})})

@require_POST
@required('admin')
def admin_worker(request,worker_id):
    w=get_worker(worker_id,False)
    if request.POST.get('action') not in ['approve','reject']:raise Http404
    db().worker_profiles.update_one({'_id':w['_id']},{'$set':{'approved':request.POST['action']=='approve','available':request.POST['action']=='approve'}})
    return redirect('admin')

def not_found(request,exception):return render(request,'error.html',{'title':'A wrong turn, perhaps?','description':'This page could not be found. Let’s get you back to the neighbourhood.'},status=404)
