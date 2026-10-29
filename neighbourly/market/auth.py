import hashlib, secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from django.conf import settings
from django.shortcuts import redirect, render
from market.db import db
COOKIE = 'neighbourly_session'
def now(): return datetime.now(timezone.utc)
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def establish(response, user, request):
    old = request.COOKIES.get(COOKIE)
    if old: db().sessions.delete_one({'token_hash': digest(old)})
    token = secrets.token_urlsafe(40)
    db().sessions.insert_one({'token_hash': digest(token), 'user_id': user['_id'], 'expires_at': now() + timedelta(hours=12)})
    response.set_cookie(COOKIE, token, max_age=43200, httponly=True, secure=settings.SESSION_COOKIE_SECURE, samesite='Lax')
    return response

def required(*roles):
    def decorate(fn):
        @wraps(fn)
        def wrapped(request, *a, **kw):
            if not request.account: return redirect('login')
            if roles and request.account['role'] not in roles:
                return render(request, 'error.html', {'title': 'This space is private', 'description': 'Your account does not have access to this page.'}, status=403)
            return fn(request, *a, **kw)
        return wrapped
    return decorate

def throttle(request):
    # Per direct peer IP and fixed 15 minute window; do not trust forwarded headers.
    current = now(); key = digest(request.META.get('REMOTE_ADDR', 'local')) + ':' + str(int(current.timestamp()) // 900)
    row = db().rate_limits.find_one_and_update({'_id': key}, {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': current + timedelta(minutes=16)}}, upsert=True, return_document=True)
    return row['count'] > 30
