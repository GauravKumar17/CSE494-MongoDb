from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.hashers import make_password
from django.conf import settings
from market.auth import now
from market.db import db,indexes
DEMO_PASSWORD='NeighbourlyDemo!2026'
class Command(BaseCommand):
    help='Add clearly labelled synthetic profiles and demo accounts; development only.'
    def handle(self,*args,**opts):
        if not settings.DEBUG:raise CommandError('Demo seeding requires DJANGO_DEBUG=True. Do not seed production.')
        indexes();d=db()
        def user(email,name,role):
            d.users.update_one({'email':email},{'$setOnInsert':{'name':name,'role':role,'active':True,'password_hash':make_password(DEMO_PASSWORD),'created_at':now(),'is_demo':True}},upsert=True)
            return d.users.find_one({'email':email})
        user('customer@example.com','Gaurav Kumar','customer')
        user('admin@example.com','Demo Administrator','admin')
        records=[('Ravi Kumar','electrical','Phagwara',8,399,'Switch and socket repair, Fan installation, Light fittings'),('Amanpreet Singh','plumbing','Phagwara',6,349,'Tap repair, Leak diagnosis, Sink fittings'),('Meera Sharma','painting','Jalandhar',5,499,'Wall touch-ups, Interior painting, Colour consultation'),('Sandeep Verma','carpentry','Phagwara',10,449,'Door repair, Shelf fitting, Furniture care'),('Priya Das','cleaning','Jalandhar',4,299,'Kitchen cleaning, Bathroom care, Common areas'),('Arjun Patel','appliance','Phagwara',7,399,'Appliance diagnosis, Fan repair, Routine maintenance')]
        for i,(name,category,locality,experience,rate,skills) in enumerate(records):
            email='worker@example.com' if i==0 else f'worker{i+1}@example.com'
            u=user(email,name,'worker')
            d.worker_profiles.update_one({'user_id':u['_id']},{'$setOnInsert':{'name':name,'category':category,'locality':locality,'experience':experience,'rate_paise':rate*100,'skills':skills.split(', '),'bio':f'I help neighbours with {skills.lower()}. I value clear communication, careful work and leaving your home a little better than I found it. This is a synthetic profile for the college demonstration.','approved':True,'available':True,'created_at':now(),'is_demo':True}},upsert=True)
        self.stdout.write(self.style.SUCCESS('Synthetic demo data added. See README for development-only login details.'))
