import getpass
from django.core.management.base import BaseCommand,CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from pymongo.errors import DuplicateKeyError
from market.db import db,indexes
from market.auth import now
class Command(BaseCommand):
    help='Create an administrator account interactively. Password is never printed.'
    def add_arguments(self,parser):
        parser.add_argument('--email',required=True);parser.add_argument('--name',default='Administrator')
    def handle(self,*args,**opts):
        email=opts['email'].strip().lower()
        try:validate_email(email)
        except ValidationError as e:raise CommandError(str(e))
        password=getpass.getpass('Password: ')
        if password!=getpass.getpass('Confirm password: '):raise CommandError('Passwords do not match.')
        try:validate_password(password)
        except ValidationError as e:raise CommandError(str(e))
        indexes()
        try:db().users.insert_one({'name':opts['name'],'email':email,'role':'admin','password_hash':make_password(password),'active':True,'created_at':now()})
        except DuplicateKeyError:raise CommandError('This email already exists. No account was changed.')
        self.stdout.write(self.style.SUCCESS('Administrator created. Log in through /login/.'))
