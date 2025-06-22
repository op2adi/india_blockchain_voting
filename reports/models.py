from django.db import models
from django.contrib.auth import get_user_model
from elections.models import Election
from users.models import Constituency, AdminUser
import uuid
from elections.models import Election
from users.models import Constituency, AdminUser
class VotingReport(models.Model):
    """Digital voting reports and receipts"""
    REPORT_TYPES = [
        ('CONSTITUENCY_RESULTS', 'Constituency Results'),
        ('PARTY_PERFORMANCE', 'Party Performance'),
        ('VOTER_TURNOUT', 'Voter Turnout'),
        ('ELECTION_SUMMARY', 'Election Summary'),sults'),
        ('CANDIDATE_WISE', 'Candidate Wise Report'),
    ]   ('VOTER_TURNOUT', 'Voter Turnout'),
        ('ELECTION_SUMMARY', 'Election Summary'),
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='reports')
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, blank=True, null=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)lated_name='reports')
    title = models.CharField(max_length=200)uency, on_delete=models.CASCADE, blank=True, null=True)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    # Report datas.CharField(max_length=200)
    report_data = models.JSONField()lank=True)
    
    # Generated files
    pdf_file = models.FileField(upload_to='reports/pdf/', blank=True)
    excel_file = models.FileField(upload_to='reports/excel/', blank=True)
    # Generated files
    # Metadata models.FileField(upload_to='reports/pdf/', blank=True)
    generated_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    # Metadata
    # Access controlodels.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=False)dd=True)
    download_count = models.IntegerField(default=0)
    # Access control
    # Digital signatureBooleanField(default=False)
    digital_signature = models.TextField(blank=True)
    verification_hash = models.CharField(max_length=64, blank=True)
    # Digital signature
    class Meta:nature = models.TextField(blank=True)
        ordering = ['-generated_at']ield(max_length=64, blank=True)
        indexes = [
            models.Index(fields=['election', 'report_type']),
            models.Index(fields=['generated_at']),
        ]ndexes = [
            models.Index(fields=['election', 'report_type']),
    created_at = models.DateTimeField(auto_now_add=True)ex(fields=['generated_at']),
    updated_at = models.DateTimeField(auto_now=True)
        
    def __str__(self):    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"{self.election.name}"


class AuditReport(models.Model):
    """System audit logs for security and compliance"""
    ACTION_CHOICES = [id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        ('LOGIN', 'User Login'),CharField(max_length=200)
        ('LOGOUT', 'User Logout'),
        ('REGISTER', 'User Registration'),
        ('VOTE_CAST', 'Vote Cast'),# Report period
        ('PROFILE_UPDATE', 'Profile Update'),d_start = models.DateTimeField()
        ('PASSWORD_CHANGE', 'Password Change'),imeField()
        ('ADMIN_ACTION', 'Admin Action'),
        ('API_ACCESS', 'API Access'),
        ('BLOCKCHAIN_EVENT', 'Blockchain Event'),
    ]
    d files
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    # Metadata
    # Action detailss.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)True)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)# Publication status
    user_agent = models.TextField(blank=True)ls.BooleanField(default=False)
    
    # Additional context
    details = models.JSONField(default=dict, blank=True)# Digital signature
    nature = models.TextField(blank=True)
    # Related recordsield(max_length=64, blank=True)
    election = models.ForeignKey(Election, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location data (if available)
    latitude = models.FloatField(null=True, blank=True)    
    longitude = models.FloatField(null=True, blank=True)    def __str__(self):
    itle}"
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action']),s"""
            models.Index(fields=['timestamp']),id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
            models.Index(fields=['user']),eld(max_length=200)
        ]ank=True)
    
    def __str__(self):# Performance metrics
        user_str = self.user.voter_id if self.user else "Anonymous"dels.JSONField()
        return f"{self.get_action_display()} by {user_str} at {self.timestamp}"

d files
class PerformanceReport(models.Model):
    """System performance metrics"""
    METRIC_CHOICES = [# Metadata
        ('API_RESPONSE_TIME', 'API Response Time'),odels.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
        ('DATABASE_QUERY_TIME', 'Database Query Time'),dd=True)
        ('VOTE_PROCESSING_TIME', 'Vote Processing Time'),
        ('BLOCKCHAIN_BLOCK_TIME', 'Blockchain Block Generation Time'),# Access control
        ('CONCURRENT_USERS', 'Concurrent Users'), models.BooleanField(default=False)
        ('MEMORY_USAGE', 'Memory Usage'),ield(default=0)
        ('CPU_USAGE', 'CPU Usage'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)    
    metric = models.CharField(max_length=30, choices=METRIC_CHOICES)    def __str__(self):
    value = models.FloatField(): {self.title}"
    
    # Context
    context = models.JSONField(default=dict, blank=True)
    
    # Related entityname = models.CharField(max_length=100, unique=True)
    election = models.ForeignKey(Election, on_delete=models.SET_NULL, null=True, blank=True)tField(blank=True)
    ength=30)
    class Meta:
        ordering = ['-timestamp']# Template configuration
        indexes = [_config = models.JSONField()
            models.Index(fields=['metric']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
        return f"{self.get_metric_display()}: {self.value} at {self.timestamp}"= models.DateTimeField(auto_now_add=True)
eTimeField(auto_now=True)

class ReportTemplate(models.Model):
    """Templates for generating reports"""e']
    name = models.CharField(max_length=100, unique=True)    
    description = models.TextField(blank=True)    def __str__(self):
    report_type = models.CharField(max_length=30)
    
    # Template configuration
    template_config = models.JSONField().Model):
    css_styles = models.TextField(blank=True)ation"""
    
    # Status
    is_active = models.BooleanField(default=True)   ('WEEKLY', 'Weekly'),
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)    ('MONTHLY', 'Monthly'),
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:name = models.CharField(max_length=100)
        ordering = ['name']rField(max_length=30)
    gth=20, choices=FREQUENCY_CHOICES)
    def __str__(self):
        return self.nameonfiguration


class ReportSchedule(models.Model):ents
    """Scheduled report generation"""ist)
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),is_active = models.BooleanField(default=True)
        ('MONTHLY', 'Monthly'),
        ('CUSTOM', 'Custom'),e)
    ]
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)= models.DateTimeField(auto_now_add=True)
    report_type = models.CharField(max_length=30)eTimeField(auto_now=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # Schedule configuration
    schedule_config = models.JSONField()    





















































        return f"Receipt {self.verification_code} for {self.election.name}"    def __str__(self):                ]            models.Index(fields=['verification_code']),            models.Index(fields=['voter_hash']),        indexes = [        ordering = ['-timestamp']    class Meta:        receipt_pdf = models.FileField(upload_to='receipts/', blank=True)    # Digital signature        verified = models.BooleanField(default=False)    verification_code = models.CharField(max_length=20, unique=True)    # Verification data        block_id = models.IntegerField(null=True, blank=True)  # Will be filled when block is mined    transaction_hash = models.CharField(max_length=64)    # Receipt data        timestamp = models.DateTimeField(auto_now_add=True)    constituency = models.ForeignKey(Constituency, on_delete=models.PROTECT)    election = models.ForeignKey(Election, on_delete=models.PROTECT)    # Election details        voter_hash = models.CharField(max_length=64)    # Anonymized voter reference (hash of voter_id + salt)        id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)    """Digital receipts for voters after casting votes"""class VoterReceipt(models.Model):        return f"{self.name} ({self.frequency})"    def __str__(self):            ordering = ['name']    class Meta:        updated_at = models.DateTimeField(auto_now=True)    created_at = models.DateTimeField(auto_now_add=True)    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)        next_run = models.DateTimeField(blank=True, null=True)    last_run = models.DateTimeField(blank=True, null=True)    is_active = models.BooleanField(default=True)    # Status        email_recipients = models.JSONField(default=list)    # Recipients        def __str__(self):
        return f"{self.name} ({self.frequency})"
