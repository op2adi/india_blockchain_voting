import csv
from io import StringIO
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import make_password
from users.models import Voter, Constituency, State

class Command(BaseCommand):
    help = 'Import voters from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Check required fields
                required_fields = ['first_name', 'last_name', 'voter_id', 'email', 
                                  'date_of_birth', 'gender', 'state', 'constituency', 
                                  'mobile_number', 'address_line1', 'city', 'pincode']
                
                for field in required_fields:
                    if field not in reader.fieldnames:
                        raise CommandError(f"CSV is missing required field: {field}")
                
                voters_added = 0
                voters_skipped = 0
                errors = []
                
                for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header row
                    try:
                        # Check if voter already exists
                        if Voter.objects.filter(voter_id=row['voter_id']).exists():
                            voters_skipped += 1
                            continue
                        
                        # Find state and constituency
                        try:
                            state = State.objects.get(name=row['state'])
                        except State.DoesNotExist:
                            try:
                                state = State.objects.get(code=row['state'])
                            except State.DoesNotExist:
                                errors.append(f"Row {row_num}: State '{row['state']}' does not exist")
                                voters_skipped += 1
                                continue
                        
                        try:
                            constituency = Constituency.objects.get(name=row['constituency'], state=state)
                        except Constituency.DoesNotExist:
                            errors.append(f"Row {row_num}: Constituency '{row['constituency']}' does not exist in state '{state.name}'")
                            voters_skipped += 1
                            continue
                        
                        # Create voter
                        voter = Voter(
                            first_name=row['first_name'],
                            last_name=row['last_name'],
                            voter_id=row['voter_id'],
                            email=row['email'],
                            date_of_birth=row['date_of_birth'],
                            gender=row['gender'],
                            state=state,
                            constituency=constituency,
                            mobile_number=row['mobile_number'],
                            address_line1=row['address_line1'],
                            address_line2=row.get('address_line2', ''),
                            city=row['city'],
                            pincode=row['pincode'],
                            is_active=True,
                            is_verified=True,
                            encrypted_voter_card_number='encrypted_placeholder'
                        )
                        
                        # Set password
                        if 'password' in row and row['password']:
                            voter.password = make_password(row['password'])
                        else:
                            # Default password is the voter_id
                            voter.password = make_password(row['voter_id'])
                        
                        voter.save()
                        voters_added += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        voters_skipped += 1
                
                self.stdout.write(self.style.SUCCESS(f'Successfully added {voters_added} voters'))
                if voters_skipped > 0:
                    self.stdout.write(self.style.WARNING(f'Skipped {voters_skipped} voters'))
                
                if errors:
                    self.stdout.write(self.style.ERROR('Errors encountered:'))
                    for error in errors[:10]:  # Show first 10 errors
                        self.stdout.write(self.style.ERROR(f'  - {error}'))
                    
                    if len(errors) > 10:
                        self.stdout.write(self.style.ERROR(f'  ... and {len(errors) - 10} more errors'))
                
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            raise CommandError(f"Error importing voters: {str(e)}")
