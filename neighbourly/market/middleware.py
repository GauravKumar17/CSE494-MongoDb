from django.shortcuts import render
from pymongo.errors import PyMongoError
from market.db import db
from market.auth import COOKIE, digest, now
class AccountMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        request.account = None
        try:
            token = request.COOKIES.get(COOKIE)
            if token:
                session = db().sessions.find_one({'token_hash': digest(token), 'expires_at': {'$gt': now()}})
                if session: request.account = db().users.find_one({'_id': session['user_id'], 'active': True}, {'password_hash': 0})
            return self.get_response(request)
        except PyMongoError:
            return render(request, 'error.html', {'title': 'A little maintenance', 'description': 'We cannot reach the database. Start MongoDB and check your .env connection settings.'}, status=503)
    def process_exception(self, request, exception):
        if isinstance(exception, PyMongoError):
            return render(request, 'error.html', {'title': 'A little maintenance', 'description': 'We cannot reach the database. Start MongoDB and check your connection settings.'}, status=503)
