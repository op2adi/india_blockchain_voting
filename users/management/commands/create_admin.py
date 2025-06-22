from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

class Command(BaseCommand):
    help = 'Creates an admin user with the specified credentials'

    def handle(self, *args, **kwargs):
        username = 'rt'
        password = 'cQKNv_W6E9qk_n2'
        email = 'admin@blockchainvoting.gov.in'
        
        try:
            with transaction.atomic():
                if User.objects.filter(username=username).exists():
                    self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists.'))
                    return
                
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f'Admin user "{username}" created successfully!'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))
