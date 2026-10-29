from django.core.management.base import BaseCommand
from market.db import db, indexes
class Command(BaseCommand):
    help='Create MongoDB indexes and document validators. No SQL migrations are needed.'
    def handle(self,*args,**options):
        d=db();d.command('ping');indexes()
        schemas={
          'users': {'required':['name','email','role','password_hash','active'], 'properties':{'name':{'bsonType':'string'},'email':{'bsonType':'string'},'role':{'enum':['customer','worker','admin']},'password_hash':{'bsonType':'string'},'active':{'bsonType':'bool'}}},
          'worker_profiles': {'required':['user_id','category','rate_paise','approved'], 'properties':{'user_id':{'bsonType':'objectId'},'category':{'enum':['electrical','plumbing','painting','cleaning','carpentry','appliance']},'rate_paise':{'bsonType':['int','long'],'minimum':10000},'approved':{'bsonType':'bool'}}},
          'bookings': {'required':['customer_id','worker_id','status','active','slot_key','price_paise'], 'properties':{'customer_id':{'bsonType':'objectId'},'worker_id':{'bsonType':'objectId'},'price_paise':{'bsonType':['int','long'],'minimum':0},'status':{'enum':['requested','confirmed','in_progress','completion_pending','completed','cancelled','declined']},'active':{'bsonType':'bool'}}},
          'reviews': {'required':['booking_id','customer_id','worker_id','rating','comment'], 'properties':{'booking_id':{'bsonType':'objectId'},'rating':{'bsonType':'int','minimum':1,'maximum':5},'comment':{'bsonType':'string'}}},
        }
        for collection,schema in schemas.items():
            validator={'$jsonSchema':{'bsonType':'object',**schema}}
            if collection in d.list_collection_names():d.command('collMod',collection,validator=validator,validationLevel='strict')
            else:d.create_collection(collection,validator=validator)
        self.stdout.write(self.style.SUCCESS('MongoDB indexes and validators are ready.'))
