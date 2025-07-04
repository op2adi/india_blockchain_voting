from django.core.management.base import BaseCommand
import csv
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Generate sample CSV data for voters, candidates, or parties.'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, choices=['voters', 'candidates', 'parties'], default='voters', help='Type of data to generate')
        parser.add_argument('--count', type=int, default=10, help='Number of rows to generate')
        parser.add_argument('--output', type=str, default=None, help='Output CSV file path')

    def handle(self, *args, **options):
        fake = Faker()
        data_type = options['type']
        count = options['count']
        output = options['output']

        if data_type == 'voters':
            header = ['first_name', 'last_name', 'voter_id', 'email', 'date_of_birth', 'gender', 'state', 'constituency', 'mobile_number', 'address_line1', 'city', 'pincode']
            rows = [
                [fake.first_name(), fake.last_name(), f"ABC{fake.random_number(digits=7, fix_len=True)}", fake.email(), fake.date_of_birth(minimum_age=18, maximum_age=90), random.choice(['M','F','O']), 'State1', 'Constituency1', f"+91{fake.random_number(digits=10, fix_len=True)}", fake.address().replace('\n', ' '), fake.city(), fake.postcode()[:6]]
                for _ in range(count)
            ]
        elif data_type == 'candidates':
            header = ['name', 'party', 'constituency', 'father_name', 'date_of_birth', 'gender', 'address']
            rows = [
                [fake.name(), 'Demo Party', 'Constituency1', fake.name(), fake.date_of_birth(minimum_age=25, maximum_age=80), random.choice(['M','F','O']), fake.address().replace('\n', ' ')]
                for _ in range(count)
            ]
        else:
            header = ['name', 'abbreviation', 'recognition_status']
            rows = [
                [fake.company(), fake.company_suffix()[:3].upper(), random.choice(['National', 'State'])]
                for _ in range(count)
            ]

        if output:
            with open(output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
            self.stdout.write(self.style.SUCCESS(f'Sample {data_type} CSV written to {output}'))
        else:
            writer = csv.writer(self.stdout)
            writer.writerow(header)
            writer.writerows(rows)
