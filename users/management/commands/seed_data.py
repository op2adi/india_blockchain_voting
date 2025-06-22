from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from users.models import State, Constituency
from elections.models import Party, Candidate, Election
import csv
import os


class Command(BaseCommand):
    help = 'Seed initial data: create superuser and import states, constituencies, parties, candidates.'

    def handle(self, *args, **options):
        # Create superuser
        User = get_user_model()
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        if not User.objects.filter(email=admin_email).exists():
            self.stdout.write('Creating superuser...')
            User.objects.create_superuser(
                username='admin',
                email=admin_email,
                password=admin_password
            )
        else:
            self.stdout.write('Superuser already exists.')

        # Base data folder
        data_dir = os.path.join(settings.BASE_DIR, 'data')

        # Import States
        states_file = os.path.join(data_dir, 'states.csv')
        if os.path.exists(states_file):
            with open(states_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    State.objects.get_or_create(
                        name=row['name'], code=row['code']
                    )
            self.stdout.write('Imported states CSV.')
        else:
            self.stdout.write('states.csv not found in data/.')

        # Import Constituencies
        constituencies_file = os.path.join(data_dir, 'constituencies.csv')
        if os.path.exists(constituencies_file):
            with open(constituencies_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    state = State.objects.filter(code=row['state_code']).first()
                    if state:
                        Constituency.objects.get_or_create(
                            name=row['name'], code=row['code'], state=state
                        )
            self.stdout.write('Imported constituencies CSV.')
        else:
            self.stdout.write('constituencies.csv not found in data/.')

        # Import Parties
        parties_file = os.path.join(data_dir, 'parties.csv')
        if os.path.exists(parties_file):
            with open(parties_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    Party.objects.get_or_create(
                        name=row['name'], abbreviation=row['abbreviation'], defaults={
                            'recognition_status': row.get('recognition_status', 'UNRECOGNIZED')
                        }
                    )
            self.stdout.write('Imported parties CSV.')
        else:
            self.stdout.write('parties.csv not found in data/.')

        # Import Elections and Candidates
        # Similar CSV structure for elections.csv and candidates.csv can be added
        self.stdout.write(self.style.SUCCESS('Seeding data complete.'))
