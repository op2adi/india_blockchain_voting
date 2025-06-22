from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import Constituency, State, Voter
from blockchain.models import Blockchain, Block
import uuid


class Party(models.Model):
    """Political parties"""
    name = models.CharField(max_length=200, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    symbol = models.CharField(max_length=100)
    symbol_image = models.ImageField(upload_to='party_symbols/', blank=True)
    
    # Party details
    founded_date = models.DateField(blank=True, null=True)
    headquarters = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    
    # Recognition status
    RECOGNITION_CHOICES = [
        ('NATIONAL', 'National Party'),
        ('STATE', 'State Party'),
        ('REGIONAL', 'Regional Party'),
        ('UNRECOGNIZED', 'Unrecognized'),
    ]
    recognition_status = models.CharField(max_length=20, choices=RECOGNITION_CHOICES)
    recognized_states = models.ManyToManyField(State, blank=True)
    
    # Visual identity
    party_color = models.CharField(max_length=7, default='#000000')  # Hex color
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Parties"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class Election(models.Model):
    """Election events"""
    ELECTION_TYPES = [
        ('LOK_SABHA', 'Lok Sabha General Election'),
        ('VIDHAN_SABHA', 'Vidhan Sabha Election'),
        ('RAJYA_SABHA', 'Rajya Sabha Election'),
        ('MUNICIPAL', 'Municipal Election'),
        ('PANCHAYAT', 'Panchayat Election'),
        ('BY_ELECTION', 'By-Election'),
    ]
    
    name = models.CharField(max_length=200)
    election_type = models.CharField(max_length=20, choices=ELECTION_TYPES)
    election_id = models.CharField(max_length=50, unique=True)
    
    # Geographic scope
    state = models.ForeignKey(State, on_delete=models.CASCADE, blank=True, null=True)
    constituencies = models.ManyToManyField(Constituency, through='ElectionConstituency')
    
    # Election timeline
    announcement_date = models.DateTimeField()
    nomination_start_date = models.DateTimeField()
    nomination_end_date = models.DateTimeField()
    voting_start_date = models.DateTimeField()
    voting_end_date = models.DateTimeField()
    result_date = models.DateTimeField()
    
    # Status
    STATUS_CHOICES = [
        ('ANNOUNCED', 'Announced'),
        ('NOMINATION_OPEN', 'Nomination Open'),
        ('NOMINATION_CLOSED', 'Nomination Closed'),
        ('VOTING_OPEN', 'Voting Open'),
        ('VOTING_CLOSED', 'Voting Closed'),
        ('COUNTING', 'Counting'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ANNOUNCED')
    
    # Blockchain integration
    blockchain = models.OneToOneField(Blockchain, on_delete=models.CASCADE, blank=True, null=True)
    
    # Election configuration
    allow_nota = models.BooleanField(default=True)
    require_photo_id = models.BooleanField(default=True)
    enable_face_verification = models.BooleanField(default=False)
    
    # Metadata
    description = models.TextField(blank=True)
    created_by = models.ForeignKey('users.AdminUser', on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-voting_start_date']
    
    def __str__(self):
        return f"{self.name} ({self.election_type})"
    
    def is_voting_open(self):
        """Check if voting is currently open"""
        now = timezone.now()
        return (self.status == 'VOTING_OPEN' and 
                self.voting_start_date <= now <= self.voting_end_date)
    
    def can_accept_votes(self):
        """Check if election can accept votes"""
        return self.is_voting_open() and self.blockchain is not None


class ElectionConstituency(models.Model):
    """Many-to-many relationship between Election and Constituency"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    
    # Constituency-specific election settings
    polling_start_time = models.TimeField(default='07:00:00')
    polling_end_time = models.TimeField(default='18:00:00')
    
    # Results
    total_votes_cast = models.IntegerField(default=0)
    total_valid_votes = models.IntegerField(default=0)
    total_invalid_votes = models.IntegerField(default=0)
    voter_turnout_percentage = models.FloatField(default=0.0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['election', 'constituency']
    
    def __str__(self):
        return f"{self.election.name} - {self.constituency.name}"


class Candidate(models.Model):
    """Election candidates"""
    # Personal information
    name = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200)
    mother_name = models.CharField(max_length=200, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ])
    
    # Political affiliation
    party = models.ForeignKey(Party, on_delete=models.CASCADE, blank=True, null=True)
    is_independent = models.BooleanField(default=False)
    
    # Election details
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    candidate_number = models.IntegerField()  # Serial number on ballot
    
    # Nomination details
    nomination_id = models.CharField(max_length=50, unique=True)
    nomination_date = models.DateTimeField()
    nomination_status = models.CharField(max_length=20, choices=[
        ('FILED', 'Filed'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
    ], default='FILED')
    
    # Personal details for voters
    education = models.CharField(max_length=200, blank=True)
    profession = models.CharField(max_length=200, blank=True)
    assets_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    criminal_cases = models.IntegerField(default=0)
    
    # Contact information
    address = models.TextField()
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    
    # Visual
    photo = models.ImageField(upload_to='candidate_photos/', blank=True)
    symbol = models.CharField(max_length=100, blank=True)
    symbol_image = models.ImageField(upload_to='candidate_symbols/', blank=True)
    
    # Results
    votes_received = models.IntegerField(default=0)
    vote_percentage = models.FloatField(default=0.0)
    rank = models.IntegerField(blank=True, null=True)
    is_winner = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['candidate_number']
        unique_together = [
            ['election', 'constituency', 'candidate_number'],
            ['nomination_id']
        ]
    
    def __str__(self):
        party_info = f" ({self.party.abbreviation})" if self.party else " (IND)"
        return f"{self.name}{party_info} - {self.constituency.name}"


class VoteRecord(models.Model):
    """Individual vote records"""
    # Unique vote identifier
    vote_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Election details
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, blank=True, null=True)
    
    # Blockchain data
    block = models.ForeignKey('blockchain.Block', on_delete=models.CASCADE, blank=True, null=True)
    transaction_hash = models.CharField(max_length=128, blank=True)
    
    # Vote metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)
    
    # We don't store voter identity for privacy
    # Instead we store an anonymous voter hash that can be verified by the voter
    voter_hash = models.CharField(max_length=512)
    
    class Meta:
        verbose_name = "Vote Record"
        verbose_name_plural = "Vote Records"
        
    def __str__(self):
        return f"Vote {self.vote_id} - {self.election.name}"
    
    def verify_vote(self, voter_hash):
        """Verify that this vote belongs to a specific voter"""
        return self.voter_hash == voter_hash


class VoteReceipt(models.Model):
    """Digital receipt for each vote"""
    # Receipt identifier
    receipt_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Vote record reference (no direct link to voter for privacy)
    vote_record = models.OneToOneField(VoteRecord, on_delete=models.CASCADE)
    
    # Receipt data
    qr_code = models.ImageField(upload_to='vote_receipts/', blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    
    # Verification data
    verification_hash = models.CharField(max_length=256)
    verification_token = models.CharField(max_length=64)
    
    class Meta:
        verbose_name = "Vote Receipt"
        verbose_name_plural = "Vote Receipts"
        
    def __str__(self):
        return f"Receipt {self.receipt_id}"
    
    def generate_qr_code(self):
        """Generate a QR code for this receipt"""
        # Implementation will use qrcode library
        import qrcode
        from io import BytesIO
        from django.core.files import File
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        # Add data to QR code
        verification_url = f"/verify-vote/{self.verification_token}/"
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        # Create image from QR code
        img = qr.make_image()
        
        # Save to model field
        buffer = BytesIO()
        img.save(buffer)
        filename = f'vote-receipt-{self.receipt_id}.png'
        
        self.qr_code.save(filename, File(buffer), save=False)
        self.save()


class ElectionResult(models.Model):
    """Compiled election results"""
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='results')
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    
    # Vote statistics
    total_voters = models.IntegerField()
    total_votes_cast = models.IntegerField()
    total_valid_votes = models.IntegerField()
    total_invalid_votes = models.IntegerField()
    nota_votes = models.IntegerField(default=0)
    
    # Turnout
    voter_turnout_percentage = models.FloatField()
    
    # Winner information
    winning_candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    winning_party = models.ForeignKey(Party, on_delete=models.CASCADE, blank=True, null=True)
    winning_margin = models.IntegerField()
    victory_margin_percentage = models.FloatField()
    
    # Result status
    RESULT_STATUS = [
        ('COUNTING', 'Counting in Progress'),
        ('PROVISIONAL', 'Provisional Result'),
        ('FINAL', 'Final Result'),
        ('DISPUTED', 'Disputed'),
    ]
    status = models.CharField(max_length=20, choices=RESULT_STATUS, default='COUNTING')
    
    # Verification
    result_hash = models.CharField(max_length=64)  # Hash of all vote data
    blockchain_verified = models.BooleanField(default=False)
    
    # Timestamps
    counting_start_time = models.DateTimeField(blank=True, null=True)
    result_declared_time = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['election', 'constituency']
        ordering = ['-result_declared_time']
    
    def __str__(self):
        return f"{self.election.name} - {self.constituency.name} Result"


class CandidateVoteCount(models.Model):
    """Vote count for each candidate"""
    election_result = models.ForeignKey(ElectionResult, on_delete=models.CASCADE, related_name='candidate_votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    
    votes_count = models.IntegerField()
    vote_percentage = models.FloatField()
    rank = models.IntegerField()
    
    # Round-wise counting (for complex elections)
    round_number = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['election_result', 'candidate', 'round_number']
        ordering = ['-votes_count']
    
    def __str__(self):
        return f"{self.candidate.name}: {self.votes_count} votes"


class ElectionAuditLog(models.Model):
    """Audit log for election-related activities"""
    ACTION_CHOICES = [
        ('VOTE_CAST', 'Vote Cast'),
        ('VOTE_VERIFIED', 'Vote Verified'),
        ('RESULT_CALCULATED', 'Result Calculated'),
        ('ELECTION_STARTED', 'Election Started'),
        ('ELECTION_ENDED', 'Election Ended'),
        ('CANDIDATE_ADDED', 'Candidate Added'),
        ('VOTER_VERIFIED', 'Voter Verified'),
    ]
    
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    
    # Actor information
    actor_type = models.CharField(max_length=50)  # voter, admin, system
    actor_id = models.CharField(max_length=255)
    
    # Action details
    details = models.JSONField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Context
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['election', 'action']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} in {self.election.name} by {self.actor_type}"
