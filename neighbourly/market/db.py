from functools import lru_cache
from django.conf import settings
from pymongo import MongoClient, ASCENDING
@lru_cache(maxsize=1)
def client():
    return MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=4000, tz_aware=True)
def db():
    return client()[settings.MONGODB_DATABASE]
def indexes():
    d = db()
    d.users.create_index('email', unique=True)
    d.worker_profiles.create_index('user_id', unique=True)
    d.worker_profiles.create_index([('approved', 1), ('category', 1), ('locality', 1)])
    d.bookings.create_index([('worker_id', 1), ('slot_key', 1)], unique=True, partialFilterExpression={'active': True})
    d.bookings.create_index([('customer_id', 1), ('created_at', -1)])
    d.bookings.create_index([('worker_id', 1), ('created_at', -1)])
    d.reviews.create_index('booking_id', unique=True)
    d.sessions.create_index('token_hash', unique=True)
    d.sessions.create_index('expires_at', expireAfterSeconds=0)
    d.rate_limits.create_index('expires_at', expireAfterSeconds=0)
