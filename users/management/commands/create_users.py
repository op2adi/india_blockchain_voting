import random
import string
import hashlib
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from users.models import Voter, State, Constituency


class Command(BaseCommand):
    help = 'Creates users with random passwords and sends them via email'

    def add_arguments(self, parser):
        parser.add_argument('--first_name', required=True, help='First name of the user')
        parser.add_argument('--last_name', required=True, help='Last name of the user')
        parser.add_argument('--voter_id', required=True, help='Voter ID in format ABC1234567')
        parser.add_argument('--email', required=True, help='User email address to send credentials')
        parser.add_argument('--state_id', required=True, help='State ID')
        parser.add_argument('--constituency_id', required=True, help='Constituency ID')
        parser.add_argument('--gender', required=True, choices=['M', 'F', 'O'], help='Gender (M/F/O)')
        parser.add_argument('--date_of_birth', required=True, help='Date of birth in YYYY-MM-DD format')
        parser.add_argument('--mobile_number', required=True, help='Mobile number with +91 prefix')
        parser.add_argument('--address_line1', required=True, help='Address line 1')
        parser.add_argument('--city', required=True, help='City')
        parser.add_argument('--pincode', required=True, help='6-digit pincode')
        parser.add_argument('--address_line2', default='', help='Address line 2 (optional)')
        
    def generate_random_password(self, length=12):
        """Generate a random secure password"""
        characters = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%^&*()"
        password = ''.join(random.choice(characters) for _ in range(length))
        return password

    def send_credentials_email(self, email, voter_id, password):
        """Send email with login credentials"""
        subject = 'Your Election Portal Login Credentials'
        message = f"""
Dear Voter,

Your account has been created on the India Blockchain Voting Platform.

Your login credentials are:
Voter ID: {voter_id}
Password: {password}

Please keep these credentials secure and do not share with anyone.
For security reasons, please change your password after first login.

Regards,
Election Commission of India
        """
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send email: {str(e)}"))
            return False

    def handle(self, *args, **options):
        # Extract parameters
        first_name = options['first_name']
        last_name = options['last_name']
        voter_id = options['voter_id']
        email = options['email']
        state_id = options['state_id']
        constituency_id = options['constituency_id']
        gender = options['gender']
        date_of_birth = options['date_of_birth']
        mobile_number = options['mobile_number']
        address_line1 = options['address_line1']
        address_line2 = options['address_line2']
        city = options['city']
        pincode = options['pincode']
        
        # Check if voter_id already exists
        if Voter.objects.filter(voter_id=voter_id).exists():
            self.stdout.write(self.style.ERROR(f"User with voter_id {voter_id} already exists."))
            return
        
        # Check if email already exists
        if Voter.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f"User with email {email} already exists."))
            return
        
        # Validate state and constituency
        try:
            state = State.objects.get(id=state_id)
        except State.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"State with id {state_id} does not exist."))
            return
            
        try:
            constituency = Constituency.objects.get(id=constituency_id)
            if constituency.state.id != state.id:
                self.stdout.write(self.style.ERROR(f"Constituency {constituency_id} does not belong to state {state_id}."))
                return
        except Constituency.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Constituency with id {constituency_id} does not exist."))
            return
            
        # Generate random password
        password = self.generate_random_password()
        
        try:
            # Create new user
            voter = Voter(
                first_name=first_name,
                last_name=last_name,
                voter_id=voter_id,
                email=email,
                state=state,
                constituency=constituency,
                gender=gender,
                date_of_birth=date_of_birth,
                mobile_number=mobile_number,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                pincode=pincode,
                is_verified=True,  # Admins create verified users
                verification_date=timezone.now(),
                encrypted_voter_card_number=hashlib.sha256(voter_id.encode()).hexdigest()
            )
            
            # Set the password using the secure method
            voter.set_password(password)
            voter.save()
            
            # Send email with credentials
            email_sent = self.send_credentials_email(email, voter_id, password)
            
            if email_sent:
                self.stdout.write(self.style.SUCCESS(f"Successfully created user {voter_id} and sent credentials to {email}"))
            else:
                self.stdout.write(self.style.WARNING(f"User {voter_id} created but failed to send email. Password: {password}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create user: {str(e)}"))
