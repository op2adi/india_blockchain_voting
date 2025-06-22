import mysql.connector
import random
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from faker import Faker
from users.models import Voter, State, Constituency
from elections.models import Election, Party, Candidate
from blockchain.models import Blockchain, Block, Transaction
from reports.models import VotingReport, AuditReport, VoterReceipt

class Command(BaseCommand):
    help = 'Seed database with dummy data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument('--voters', type=int, default=100, help='Number of voters to create')
        parser.add_argument('--candidates', type=int, default=20, help='Number of candidates to create')
        parser.add_argument('--transactions', type=int, default=50, help='Number of vote transactions to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')
    
    def handle(self, *args, **options):
        faker = Faker('en_IN')
        
        num_voters = options['voters']
        num_candidates = options['candidates']
        num_transactions = options['transactions']
        clear_data = options['clear']
        
        if clear_data:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            # Clear data but preserve states and constituencies
            Transaction.objects.all().delete()
            Block.objects.all().delete()
            Blockchain.objects.all().delete()
            VoterReceipt.objects.all().delete()
            AuditReport.objects.all().delete()
            VotingReport.objects.all().delete()
            Candidate.objects.all().delete()
            Voter.objects.filter(is_staff=False).delete()
        
        # Get states and constituencies
        states = list(State.objects.all())
        constituencies = list(Constituency.objects.all())
        
        if not states or not constituencies:
            self.stdout.write(self.style.ERROR('No states or constituencies found. Run seed_locations command first.'))
            return
        
        # Create parties if needed
        if Party.objects.count() == 0:
            self.stdout.write(self.style.NOTICE('Creating political parties...'))
            parties = [
                ('Bharatiya Janata Party', 'BJP', 'Lotus', 'NATIONAL', '#FF9933'),
                ('Indian National Congress', 'INC', 'Hand', 'NATIONAL', '#0078D7'),
                ('Aam Aadmi Party', 'AAP', 'Broom', 'STATE', '#1AAE9F'),
                ('Communist Party of India (Marxist)', 'CPI(M)', 'Hammer and Sickle', 'NATIONAL', '#FF0000'),
                ('All India Trinamool Congress', 'TMC', 'Flower and Grass', 'STATE', '#00FF00'),
                ('Bahujan Samaj Party', 'BSP', 'Elephant', 'NATIONAL', '#0000FF'),
                ('Samajwadi Party', 'SP', 'Bicycle', 'STATE', '#FF0000'),
            ]
            
            for name, abbr, symbol, rec, color in parties:
                Party.objects.create(
                    name=name,
                    abbreviation=abbr,
                    symbol=symbol,
                    recognition_status=rec,
                    party_color=color,
                    is_active=True
                )
        
        parties = list(Party.objects.all())
        
        # Create an election if needed
        if Election.objects.count() == 0:
            self.stdout.write(self.style.NOTICE('Creating election...'))
            now = timezone.now()
            election = Election.objects.create(
                name='General Election 2025',
                election_type='LOK_SABHA',
                election_id='GE2025',
                announcement_date=now - timezone.timedelta(days=60),
                nomination_start_date=now - timezone.timedelta(days=45),
                nomination_end_date=now - timezone.timedelta(days=30),
                voting_start_date=now - timezone.timedelta(days=7),
                voting_end_date=now + timezone.timedelta(days=7),
                result_date=now + timezone.timedelta(days=14),
                status='VOTING_OPEN',
                allow_nota=True,
                require_photo_id=True
            )
            
            # Add all constituencies to the election
            for constituency in constituencies:
                election.constituencies.add(constituency)
            
            # Create blockchain for this election
            Blockchain.objects.create(
                name=f"Election-{election.election_id}",
                election=election,
                description=f"Blockchain for {election.name}"
            )
        
        elections = list(Election.objects.all())
        
        # Create voters
        if Voter.objects.filter(is_staff=False).count() < num_voters:
            self.stdout.write(self.style.NOTICE(f'Creating {num_voters} voters...'))
            
            existing_count = Voter.objects.filter(is_staff=False).count()
            to_create = num_voters - existing_count
            
            for i in range(to_create):
                gender = random.choice(['M', 'F'])
                first_name = faker.first_name_male() if gender == 'M' else faker.first_name_female()
                last_name = faker.last_name()
                
                state = random.choice(states)
                constituency = random.choice([c for c in constituencies if c.state == state])
                
                # Generate a unique voter ID like ABC1234567
                while True:
                    voter_id = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}{random.randint(1000000, 9999999)}"
                    if not Voter.objects.filter(voter_id=voter_id).exists():
                        break
                
                Voter.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    voter_id=voter_id,
                    email=faker.email(),
                    password=make_password('password123'),
                    is_staff=False,
                    is_active=True,
                    is_verified=True,
                    date_of_birth=faker.date_of_birth(minimum_age=18, maximum_age=90),
                    gender=gender,
                    constituency=constituency,
                    state=state,
                    address_line1=faker.street_address(),
                    city=faker.city(),
                    pincode=str(faker.postcode()),
                    mobile_number=f"+91{faker.numerify('##########')}",
                    encrypted_voter_card_number='encrypted_placeholder'
                )
        
        # Create candidates
        if Candidate.objects.count() < num_candidates:
            self.stdout.write(self.style.NOTICE(f'Creating {num_candidates} candidates...'))
            
            existing_count = Candidate.objects.count()
            to_create = num_candidates - existing_count
            
            for i in range(to_create):
                gender = random.choice(['M', 'F'])
                first_name = faker.first_name_male() if gender == 'M' else faker.first_name_female()
                last_name = faker.last_name()
                
                party = random.choice(parties)
                election = random.choice(elections)
                constituency = random.choice(list(election.constituencies.all()))
                
                Candidate.objects.create(
                    name=f"{first_name} {last_name}",
                    father_name=faker.name_male(),
                    date_of_birth=faker.date_of_birth(minimum_age=25, maximum_age=75),
                    gender=gender,
                    party=party,
                    election=election,
                    constituency=constituency,
                    candidate_number=Candidate.objects.filter(election=election).count() + 1,
                    nomination_id=f"NOM-{election.id}-{faker.numerify('####')}",
                    nomination_date=election.nomination_start_date + timezone.timedelta(days=random.randint(1, 10)),
                    address=faker.address(),
                    nomination_status='ACCEPTED',
                    assets_value=random.randint(100000, 10000000),
                    criminal_cases=random.randint(0, 3)
                )
        
        # Create blockchain transactions (votes)
        blockchain = Blockchain.objects.first()
        if blockchain and Transaction.objects.count() < num_transactions:
            self.stdout.write(self.style.NOTICE(f'Creating blockchain and vote transactions...'))
            
            # Create genesis block if doesn't exist
            if not blockchain.blocks.exists():
                genesis = Block.objects.create(
                    blockchain=blockchain,
                    index=0,
                    previous_hash='0' * 64,
                    timestamp=timezone.now(),
                    nonce=0,
                    hash='genesis_block_hash',
                    merkle_root='genesis_merkle_root'
                )
            
            # Get latest block
            latest_block = blockchain.blocks.order_by('-index').first()
            
            # Create block for votes
            if latest_block.index == 0:  # Only genesis block exists
                voting_block = Block.objects.create(
                    blockchain=blockchain,
                    index=1,
                    previous_hash=latest_block.hash,
                    timestamp=timezone.now(),
                    nonce=random.randint(1000, 9999),
                    hash=uuid.uuid4().hex,
                    merkle_root=uuid.uuid4().hex
                )
            else:
                voting_block = latest_block
                
            # Create vote transactions
            existing_count = Transaction.objects.count()
            to_create = num_transactions - existing_count
            
            election = elections[0]
            candidates = list(Candidate.objects.filter(election=election))
            voters = list(Voter.objects.filter(is_staff=False))
            
            # Track voters who have already voted
            voted_voters = set(Transaction.objects.values_list('voter_id', flat=True))
            
            for i in range(to_create):
                # Select voter who hasn't voted yet
                available_voters = [v.voter_id for v in voters if v.voter_id not in voted_voters]
                if not available_voters:
                    self.stdout.write(self.style.WARNING('All voters have already voted. Skipping remaining transactions.'))
                    break
                    
                voter_id = random.choice(available_voters)
                voted_voters.add(voter_id)
                
                candidate = random.choice(candidates)
                
                # Create transaction
                tx = Transaction.objects.create(
                    block=voting_block,
                    timestamp=timezone.now(),
                    transaction_type='VOTE',
                    transaction_hash=uuid.uuid4().hex,
                    encrypted_data='encrypted_vote_data',
                    voter_id=voter_id,
                    candidate_id=candidate.id,
                    election_id=election.id,
                    constituency_id=candidate.constituency.id
                )
                
                # Create voter receipt
                VoterReceipt.objects.create(
                    voter_hash=uuid.uuid4().hex,
                    election=election,
                    constituency=candidate.constituency,
                    transaction_hash=tx.transaction_hash,
                    block_id=voting_block.index,
                    verification_code=f"VR-{faker.numerify('########')}"
                )
                
                # Create audit log
                AuditReport.objects.create(
                    action='VOTE_CAST',
                    ip_address=faker.ipv4(),
                    user_agent=faker.user_agent(),
                    details={'election_id': election.id, 'constituency_id': candidate.constituency.id},
                    election=election
                )
                
            self.stdout.write(self.style.SUCCESS('Successfully seeded the database with dummy data!'))
