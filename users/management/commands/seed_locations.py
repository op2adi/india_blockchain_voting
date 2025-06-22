import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import State, Constituency

class Command(BaseCommand):
    help = 'Seeds the database with Indian states and constituencies'

    def handle(self, *args, **options):
        # Path to the data file
        data_file = os.path.join(settings.BASE_DIR, 'data', 'states_constituencies.json')
        
        if not os.path.exists(data_file):
            self.stdout.write(self.style.ERROR(f'Data file {data_file} does not exist'))
            return
            
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
                
            # Process states and constituencies
            states_created = 0
            constituencies_created = 0
            
            for state_data in data.get('states', []):
                state, created = State.objects.get_or_create(
                    name=state_data['name'],
                    code=state_data['code']
                )
                
                if created:
                    states_created += 1
                
                # Process constituencies for this state
                for constituency_data in state_data.get('constituencies', []):
                    constituency, created = Constituency.objects.get_or_create(
                        name=constituency_data['name'],
                        code=constituency_data['code'],
                        constituency_type=constituency_data['type'],
                        state=state
                    )
                    
                    if created:
                        constituencies_created += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully seeded {states_created} states and {constituencies_created} constituencies'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding data: {str(e)}'))
