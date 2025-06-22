from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.crypto import get_random_string
from users.models import Voter, State, Constituency
import datetime

class Command(BaseCommand):
    help = 'Create a superuser for the Blockchain Voting system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating admin superuser...'))
        
        try:
            # Enable verbose logging
            import logging
            logger = logging.getLogger('django')
            logger.setLevel(logging.DEBUG)
            
            # First, ensure we have at least one state and constituency
            state, created = State.objects.get_or_create(
                name="Delhi",
                code="DL",
            )
            self.stdout.write(f"Using state: {state.name}")
            
            constituency, created = Constituency.objects.get_or_create(
                name="Delhi Central",
                code="DL001",
                constituency_type="LOK_SABHA",
                state=state,
                defaults={
                    'total_voters': 0,
                    'reserved_category': 'General',
                }
            )
            self.stdout.write(f"Using constituency: {constituency.name}")
            
            # Now create the admin user
            voter_id = "rt"  # Using 'rt' as username as requested
            
            # Check if admin already exists
            if Voter.objects.filter(voter_id=voter_id).exists():
                self.stdout.write(self.style.WARNING(f'Admin user with voter_id {voter_id} already exists.'))
                return
            
            # Generate random data for required fields
            encryption_key = get_random_string(32)
            
            # Temporarily modify the validator for voter_id to accept our custom admin ID
            from django.core.validators import RegexValidator
            
            # Save original validators to restore later
            voter_field = Voter._meta.get_field('voter_id')
            original_validators = voter_field.validators
            
            # Replace with a validator that accepts the 'rt' format
            voter_field.validators = []
            
            # Create the superuser - with a workaround for username requirement
            try:
                admin = Voter.objects.create(
                    voter_id=voter_id,
                    email='admin@blockchainvoting.gov.in',
                    first_name='Admin',
                    last_name='User',
                    date_of_birth=datetime.date(1990, 1, 1),
                    gender='M',
                    constituency=constituency,
                    state=state,
                    address_line1='Admin Building',
                    city='Delhi',
                    pincode='110001',
                    mobile_number='+919999999999',
                    encrypted_voter_card_number='ADMIN',
                    encryption_key=encryption_key,
                    is_verified=True,
                    is_superuser=True,
                    is_staff=True,
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS('Created admin user object successfully'))
            except Exception as e:
                from django.core.exceptions import ValidationError
                if isinstance(e, ValidationError):
                    for field, errors in e.error_dict.items():
                        self.stdout.write(self.style.ERROR(f"Field '{field}': {errors}"))
                self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))
                self.stdout.write(self.style.ERROR(f'Error type: {type(e).__name__}'))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                raise
            
            # Set password securely
            admin.set_password('cQKNv_W6E9qk_n2')
            admin.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin superuser with voter_id: {voter_id}'))
            self.stdout.write(self.style.SUCCESS('Login credentials:'))
            self.stdout.write(self.style.SUCCESS(f'  ID: {voter_id}'))
            self.stdout.write(self.style.SUCCESS('  Password: cQKNv_W6E9qk_n2'))
            
            # Restore original validators
            voter_field.validators = original_validators
            
        except Exception as e:
            # Make sure we restore validators even in case of error
            try:
                voter_field = Voter._meta.get_field('voter_id')
                voter_field.validators = original_validators
            except:
                pass
                
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))
