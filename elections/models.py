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
    is_winner = models.BooleanField(default=False, editable=False)
    
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
    # Vote types
    VOTE_TYPES = [
        ('CANDIDATE', 'Vote for Candidate'),
        ('NOTA', 'None of the Above'),
        ('ABSTAIN', 'Abstain from Voting'),
    ]
    
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
    vote_type = models.CharField(max_length=20, choices=VOTE_TYPES, default='CANDIDATE')
    
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
    verification_hash = models.CharField(max_length=256)
    
    # Cryptographic proof data
    merkle_proof = models.JSONField(default=dict)  # Store the Merkle proof path
    node_signature = models.TextField(blank=True)  # Digital signature from node
    blockchain_position = models.JSONField(default=dict)  # Block index and position within block
    
    # Use a function for the default to ensure a unique token each time
    def get_default_token():
        return uuid.uuid4().hex
        
    verification_token = models.CharField(max_length=64, default=get_default_token)

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
        
        # Add data to QR code - include verification token and hash
        verification_url = f"/verify-vote/{self.verification_token}/{self.verification_hash[:16]}/"
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

    def generate_cryptographic_proof(self):
        """Generate cryptographic proof that the vote is in the blockchain"""
        from blockchain.network.consensus import ConsensusManager
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        try:
            # Get the block and transaction hash
            block = self.vote_record.block
            transaction_hash = self.vote_record.transaction_hash
            
            # Get all transaction hashes in this block
            if 'transactions' in block.data:
                transaction_hashes = [tx['hash'] for tx in block.data['transactions']]
                
                # Generate Merkle proof
                merkle_proof = ConsensusManager.generate_merkle_proof(transaction_hashes, transaction_hash)
                self.merkle_proof = {
                    'proof_path': merkle_proof,
                    'transaction_hash': transaction_hash,
                    'merkle_root': block.merkle_root
                }
                
                # Store blockchain position data
                self.blockchain_position = {
                    'block_index': block.index,
                    'block_hash': block.hash,
                    'timestamp': block.timestamp.isoformat()
                }
                
                # Sign the proof with node's private key
                # In production, you would load a properly secured private key
                # For demo purposes we'll generate one (would normally be loaded from settings)
                try:
                    # Try to load private key from settings or use a temporary one
                    from django.conf import settings
                    
                    if hasattr(settings, 'BLOCKCHAIN_PRIVATE_KEY_PEM'):
                        private_key_pem = settings.BLOCKCHAIN_PRIVATE_KEY_PEM
                        private_key = serialization.load_pem_private_key(
                            private_key_pem.encode(),
                            password=None,
                            backend=default_backend()
                        )
                    else:
                        # For demo only - in production, keys should be managed securely
                        private_key = rsa.generate_private_key(
                            public_exponent=65537,
                            key_size=2048,
                            backend=default_backend()
                        )
                        
                    # Sign the receipt data
                    signature_data = f"{self.receipt_id}|{transaction_hash}|{block.hash}".encode()
                    signature = private_key.sign(
                        signature_data,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    
                    # Save the signature
                    self.node_signature = signature.hex()
                    self.save()
                    
                    return True
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error signing receipt: {str(e)}")
                    return False
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating cryptographic proof: {str(e)}")
            return False
            
    def verify_cryptographic_proof(self):
        """
        Verify the cryptographic proof that the vote is in the blockchain
        Returns a tuple of (is_valid, details)
        """
        from blockchain.network.consensus import ConsensusManager
        
        try:
            # Check if we have proof data
            if not self.merkle_proof or not self.blockchain_position:
                return False, "No cryptographic proof available"
                
            # Get the block
            from blockchain.models import Block
            block = Block.objects.filter(
                index=self.blockchain_position['block_index'],
                hash=self.blockchain_position['block_hash']
            ).first()
            
            if not block:
                return False, "Referenced block not found in blockchain"
                
            # Verify Merkle proof
            proof_valid = ConsensusManager.verify_merkle_proof(
                self.merkle_proof['transaction_hash'],
                self.merkle_proof['proof_path'],
                self.merkle_proof['merkle_root']
            )
            
            if not proof_valid:
                return False, "Merkle proof validation failed"
                
            # Verify node signature if available
            if self.node_signature:
                try:
                    from django.conf import settings
                    from cryptography.hazmat.primitives import hashes
                    from cryptography.hazmat.primitives.asymmetric import padding
                    from cryptography.hazmat.backends import default_backend
                    from cryptography.hazmat.primitives import serialization
                    
                    # Get public key
                    if hasattr(settings, 'BLOCKCHAIN_PUBLIC_KEY_PEM'):
                        public_key_pem = settings.BLOCKCHAIN_PUBLIC_KEY_PEM
                        public_key = serialization.load_pem_public_key(
                            public_key_pem.encode(),
                            backend=default_backend()
                        )
                        
                        # Verify the signature
                        signature_data = f"{self.receipt_id}|{self.merkle_proof['transaction_hash']}|{self.blockchain_position['block_hash']}".encode()
                        signature = bytes.fromhex(self.node_signature)
                        
                        public_key.verify(
                            signature,
                            signature_data,
                            padding.PSS(
                                mgf=padding.MGF1(hashes.SHA256()),
                                salt_length=padding.PSS.MAX_LENGTH
                            ),
                            hashes.SHA256()
                        )
                        
                        # If no exception raised, signature is valid
                    else:
                        return True, "Merkle proof valid but signature verification skipped (no public key)"
                        
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Signature verification failed: {str(e)}")
                    return False, f"Signature verification failed: {str(e)}"
                    
            return True, "Vote cryptographically verified in blockchain"
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error verifying cryptographic proof: {str(e)}")
            return False, f"Error during verification: {str(e)}"


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
