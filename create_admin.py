"""
Simple script to create an admin user directly using Django's ORM.
To be executed with Django shell: python manage.py shell < create_admin.py
"""

from users.models import Voter, State, Constituency
from django.utils.crypto import get_random_string
import datetime
from django.db import transaction

# Set voter_id for the admin
voter_id = "rt"

# Check if admin already exists
if Voter.objects.filter(voter_id=voter_id).exists():
    print(f'Admin user with voter_id {voter_id} already exists.')
    exit()

try:
    with transaction.atomic():
        # Get or create required state
        state, created = State.objects.get_or_create(
            name="Delhi",
            code="DL",
        )
        print(f"Using state: {state.name}")
        
        # Get or create required constituency
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
        print(f"Using constituency: {constituency.name}")
        
        # Generate encryption key
        encryption_key = get_random_string(32)
        
        # Temporarily disable voter_id validation
        voter_field = Voter._meta.get_field('voter_id')
        original_validators = voter_field.validators
        voter_field.validators = []
        
        # Create the admin user
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
        
        # Set password and save
        admin.set_password('cQKNv_W6E9qk_n2')
        admin.save()
        
        # Restore validators
        voter_field.validators = original_validators
        
        print(f'Successfully created admin superuser with voter_id: {voter_id}')
        print('Login credentials:')
        print(f'  ID: {voter_id}')
        print('  Password: cQKNv_W6E9qk_n2')
        
except Exception as e:
    print(f'Error creating admin user: {e}')
    import traceback
    print(traceback.format_exc())
