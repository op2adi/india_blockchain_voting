from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from cryptography.fernet import Fernet
import json
import base64


class State(models.Model):
    """Indian states"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.name


class Constituency(models.Model):
    """Parliamentary/Assembly constituencies"""
    CONSTITUENCY_TYPES = [
        ('LOK_SABHA', 'Lok Sabha'),
        ('VIDHAN_SABHA', 'Vidhan Sabha'),
        ('RAJYA_SABHA', 'Rajya Sabha'),
        ('MUNICIPAL', 'Municipal'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=10, unique=True)
    constituency_type = models.CharField(max_length=20, choices=CONSTITUENCY_TYPES)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='constituencies')
    
    # Geographic information
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    area_boundaries = models.JSONField(blank=True, null=True)  # GeoJSON
    
    # Meta information
    total_voters = models.IntegerField(default=0)
    reserved_category = models.CharField(max_length=50, blank=True)  # SC/ST/General
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Constituencies"
        ordering = ['state__name', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.state.name})"


class Voter(AbstractUser):
    """Custom user model for voters"""
    # Remove username, use voter_id instead
    username = None
    
    # Voter identification
    voter_id = models.CharField(
        max_length=20, 
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z]{3}\d{7}$',
            message='Voter ID must be in format: ABC1234567'
        )]
    )
    
    # Personal information (encrypted)
    encrypted_voter_card_number = models.TextField()
    encrypted_aadhaar_number = models.TextField(blank=True)
    
    # Demographic information
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ])
    
    # Address information
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, related_name='voters')
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    pincode = models.CharField(max_length=6, validators=[
        RegexValidator(regex=r'^\d{6}$', message='Pincode must be 6 digits')
    ])
    
    # Contact information
    mobile_number = models.CharField(max_length=15, validators=[
        RegexValidator(regex=r'^\+91\d{10}$', message='Mobile number must be +91 followed by 10 digits')
    ])
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    
    # Biometric data (encrypted)
    encrypted_face_encoding = models.TextField(blank=True)
    encrypted_fingerprint_data = models.TextField(blank=True)
    
    # Voting status
    has_voted = models.BooleanField(default=False)
    vote_count = models.IntegerField(default=0)
    last_voted_at = models.DateTimeField(blank=True, null=True)
    
    # Security
    two_factor_enabled = models.BooleanField(default=False)
    encryption_key = models.TextField()  # Personal encryption key
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    login_attempts = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(blank=True, null=True)
    
    USERNAME_FIELD = 'voter_id'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'date_of_birth']
    
    class Meta:
        ordering = ['voter_id']
    
    def __str__(self):
        return f"{self.voter_id} - {self.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Generate encryption key if not exists
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
        super().save(*args, **kwargs)
    
    def encrypt_field(self, data):
        """Encrypt sensitive data"""
        key = self.encryption_key.encode()
        f = Fernet(key)
        return f.encrypt(json.dumps(data).encode()).decode()
    
    def decrypt_field(self, encrypted_data):
        """Decrypt sensitive data"""
        key = self.encryption_key.encode()
        f = Fernet(key)
        return json.loads(f.decrypt(encrypted_data.encode()).decode())
    
    def set_voter_card_number(self, voter_card_number):
        """Set encrypted voter card number"""
        self.encrypted_voter_card_number = self.encrypt_field(voter_card_number)
    
    def get_voter_card_number(self):
        """Get decrypted voter card number"""
        if self.encrypted_voter_card_number:
            return self.decrypt_field(self.encrypted_voter_card_number)
        return None
    
    def set_aadhaar_number(self, aadhaar_number):
        """Set encrypted Aadhaar number"""
        self.encrypted_aadhaar_number = self.encrypt_field(aadhaar_number)
    
    def get_aadhaar_number(self):
        """Get decrypted Aadhaar number"""
        if self.encrypted_aadhaar_number:
            return self.decrypt_field(self.encrypted_aadhaar_number)
        return None
    
    def set_face_encoding(self, face_encoding):
        """Set encrypted face encoding"""
        if face_encoding is not None:
            # Convert numpy array to list for JSON serialization
            if hasattr(face_encoding, 'tolist'):
                face_encoding = face_encoding.tolist()
            self.encrypted_face_encoding = self.encrypt_field(face_encoding)
    
    def get_face_encoding(self):
        """Get decrypted face encoding"""
        if self.encrypted_face_encoding:
            return self.decrypt_field(self.encrypted_face_encoding)
        return None
    
    def can_vote(self):
        """Check if voter can vote"""
        return (self.is_active and 
                self.is_verified and 
                not self.is_locked and
                not self.has_voted)


class AdminUser(models.Model):
    """Admin users for election management"""
    ADMIN_ROLES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('ELECTION_COMMISSIONER', 'Election Commissioner'),
        ('CONSTITUENCY_ADMIN', 'Constituency Admin'),
        ('TECHNICAL_ADMIN', 'Technical Admin'),
        ('AUDIT_ADMIN', 'Audit Admin'),
    ]
    
    user = models.OneToOneField(Voter, on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=ADMIN_ROLES)
    
    # Permissions
    can_create_elections = models.BooleanField(default=False)
    can_manage_voters = models.BooleanField(default=False)
    can_view_results = models.BooleanField(default=False)
    can_audit_blockchain = models.BooleanField(default=False)
    can_manage_constituencies = models.BooleanField(default=False)
    
    # Assigned constituencies (for constituency admins)
    assigned_constituencies = models.ManyToManyField(Constituency, blank=True)
    
    # Digital signature
    public_key = models.TextField()
    private_key_encrypted = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['role', 'user__voter_id']
    
    def __str__(self):
        return f"{self.user.voter_id} - {self.role}"


class VoterVerification(models.Model):
    """Voter verification records"""
    VERIFICATION_TYPES = [
        ('AADHAAR', 'Aadhaar Verification'),
        ('FACE', 'Face Recognition'),
        ('FINGERPRINT', 'Fingerprint'),
        ('OTP', 'OTP Verification'),
        ('MANUAL', 'Manual Verification'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='verifications')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Verification data
    verification_data = models.JSONField()
    verification_score = models.FloatField(default=0.0)
    
    # Verification metadata
    verified_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, blank=True)
    verification_ip = models.GenericIPAddressField()
    verification_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Expiry
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Audit
    remarks = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-verification_timestamp']
        unique_together = ['voter', 'verification_type', 'verification_timestamp']
    
    def __str__(self):
        return f"{self.voter.voter_id} - {self.verification_type} - {self.status}"


class LoginAttempt(models.Model):
    """Track login attempts for security"""
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='login_attempts_log')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Attempt details
    success = models.BooleanField()
    failure_reason = models.CharField(max_length=100, blank=True)
    
    # Location data
    location_data = models.JSONField(blank=True, null=True)
    
    # Two-factor authentication
    used_2fa = models.BooleanField(default=False)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.voter.voter_id} - {status} - {self.timestamp}"


class VoterSession(models.Model):
    """Track active voter sessions"""
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    
    # Session metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_fingerprint = models.CharField(max_length=64)
    
    # Session status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    # Security flags
    is_suspicious = models.BooleanField(default=False)
    security_score = models.FloatField(default=100.0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.voter.voter_id} - {self.session_key[:8]}... - {'Active' if self.is_active else 'Inactive'}"
