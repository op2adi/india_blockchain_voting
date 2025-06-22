import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from faker import Faker
import mysql.connector
from decouple import config
import uuid
import csv
import os
from pathlib import Path
from users.models import Voter, State, Constituency

class Command(BaseCommand):
    help = "Seed dummy voters using MySQL connector"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=100, help='Number of voters to create')
        parser.add_argument('--output', type=str, help='Output file path for generated voter details')

    def handle(self, *args, **options):
        count = options['count']
        output_file = options.get('output')
        
        self.stdout.write(self.style.SUCCESS(f'Starting to seed {count} dummy voters...'))
        
        # Create Faker instance for India
        fake = Faker(['en_IN'])
        
        # Get states and constituencies
        states = list(State.objects.all())
        if not states:
            self.stdout.write(self.style.ERROR('No states found. Please run seed_locations command first.'))
            return
            
        # Get DB credentials
        db_host = config('DB_HOST', default='localhost')
        db_user = config('DB_USER', default='root')
        db_password = config('DB_PASSWORD', default='')
        db_name = config('DB_NAME', default='blockchain_voting')
        
        # Connect to MySQL
        try:
            conn = mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name
            )
            cursor = conn.cursor()
            self.stdout.write(self.style.SUCCESS('Successfully connected to MySQL database'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to connect to MySQL: {str(e)}'))
            return
        
        # Open output file if specified
        csv_file = None
        csv_writer = None
        if output_file:
            try:
                csv_file = open(output_file, 'w', newline='')
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(['voter_id', 'first_name', 'last_name', 'email', 'state', 'constituency', 'password'])
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating output file: {str(e)}'))
        
        voters_created = 0
        
        try:
            # Prepare SQL insert query
            insert_query = """
            INSERT INTO users_voter (
                voter_id, password, email, first_name, last_name, date_of_birth, 
                gender, constituency_id, address_line1, address_line2, city, state_id, 
                pincode, mobile_number, is_verified, verification_date, encrypted_voter_card_number,
                has_voted, vote_count, two_factor_enabled, encryption_key,
                created_at, updated_at, is_active, is_staff, is_superuser, last_login
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            """
            
            # Generate and insert dummy voters
            for i in range(count):
                # Select random state and constituency
                state = random.choice(states)
                constituencies = list(Constituency.objects.filter(state=state))
                if not constituencies:
                    continue
                constituency = random.choice(constituencies)
                
                # Generate a random Indian voter ID format: 3 capital letters + 7 digits
                voter_id = f"{fake.random_uppercase_letter()}{fake.random_uppercase_letter()}{fake.random_uppercase_letter()}{fake.random_number(digits=7)}"
                
                # Generate other details
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@example.com"
                
                # Generate password
                password = f"Pass{uuid.uuid4().hex[:8]}"
                hashed_password = make_password(password)
                
                # Personal details
                gender = random.choice(['M', 'F', 'O'])
                dob = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%Y-%m-%d')
                address_line1 = fake.street_address()
                address_line2 = fake.street_name()
                city = fake.city()
                pincode = fake.postcode()
                mobile_number = f"+91{fake.msisdn()[3:]}"  # Format as +91XXXXXXXXXX
                
                # Status fields
                is_verified = True
                verification_date = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                encrypted_voter_card_number = 'encrypted_placeholder'
                has_voted = False
                vote_count = 0
                two_factor_enabled = False
                encryption_key = 'dummy_encryption_key'
                
                # Timestamps
                created_at = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                updated_at = created_at
                
                # Auth fields
                is_active = True
                is_staff = False
                is_superuser = False
                last_login = None
                
                # Prepare data for insertion
                voter_data = (
                    voter_id, hashed_password, email, first_name, last_name, dob,
                    gender, constituency.id, address_line1, address_line2, city, state.id,
                    pincode, mobile_number, is_verified, verification_date, encrypted_voter_card_number,
                    has_voted, vote_count, two_factor_enabled, encryption_key,
                    created_at, updated_at, is_active, is_staff, is_superuser, last_login
                )
                
                # Execute the query
                cursor.execute(insert_query, voter_data)
                
                # Save to CSV if specified
                if csv_writer:
                    csv_writer.writerow([voter_id, first_name, last_name, email, state.name, constituency.name, password])
                
                # Progress indicator
                if (i+1) % 10 == 0:
                    self.stdout.write(f'Created {i+1} voters...')
                    conn.commit()
                
                voters_created += 1
            
            # Final commit
            conn.commit()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created {voters_created} dummy voters'))
            
        except Exception as e:
            conn.rollback()
            self.stdout.write(self.style.ERROR(f'Error creating dummy voters: {str(e)}'))
        
        finally:
            # Close connections
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if csv_file:
                csv_file.close()
                self.stdout.write(self.style.SUCCESS(f'Voter details saved to {output_file}'))
