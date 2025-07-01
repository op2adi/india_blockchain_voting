from django.db import models
from django.contrib.auth import get_user_model
from elections.models import Election
from users.models import Constituency, AdminUser
import uuid

class VotingReport(models.Model):
    """Digital voting reports and receipts"""
    REPORT_TYPES = [
        ('CONSTITUENCY_RESULTS', 'Constituency Results'),
        ('PARTY_PERFORMANCE', 'Party Performance'),
        ('VOTER_TURNOUT', 'Voter Turnout'),
        ('ELECTION_SUMMARY', 'Election Summary'),
        ('CANDIDATE_WISE', 'Candidate Wise Report'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='reports')
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE, blank=True, null=True)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Report data
    report_data = models.JSONField()
    
    # Generated files
    pdf_file = models.FileField(upload_to='reports/pdf/', blank=True)
    excel_file = models.FileField(upload_to='reports/excel/', blank=True)
    
    # Metadata
    generated_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Access control
    is_public = models.BooleanField(default=False)
    download_count = models.IntegerField(default=0)
    
    # Digital signature
    digital_signature = models.TextField(blank=True)
    verification_hash = models.CharField(max_length=64, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['election', 'report_type']),
            models.Index(fields=['generated_at']),
        ]
        
    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"


class AuditReport(models.Model):
    """System audit logs for security and compliance"""
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('REGISTER', 'User Registration'),
        ('VOTE_CAST', 'Vote Cast'),
        ('PROFILE_UPDATE', 'Profile Update'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('ADMIN_ACTION', 'Admin Action'),
        ('API_ACCESS', 'API Access'),
        ('BLOCKCHAIN_EVENT', 'Blockchain Event'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Additional context
    details = models.JSONField(default=dict, blank=True)
    
    # Related records
    election = models.ForeignKey(Election, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location data (if available)
    latitude = models.FloatField(null=True, blank=True)    
    longitude = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        user_str = self.user.voter_id if self.user else "Anonymous"
        return f"{self.get_action_display()} by {user_str} at {self.timestamp}"


class PerformanceReport(models.Model):
    """System performance metrics"""
    METRIC_CHOICES = [
        ('API_RESPONSE_TIME', 'API Response Time'),
        ('DATABASE_QUERY_TIME', 'Database Query Time'),
        ('VOTE_PROCESSING_TIME', 'Vote Processing Time'),
        ('BLOCKCHAIN_BLOCK_TIME', 'Blockchain Block Generation Time'),
        ('CONCURRENT_USERS', 'Concurrent Users'),
        ('MEMORY_USAGE', 'Memory Usage'),
        ('CPU_USAGE', 'CPU Usage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)    
    metric = models.CharField(max_length=30, choices=METRIC_CHOICES)
    value = models.FloatField()
    
    # Context
    context = models.JSONField(default=dict, blank=True)
    
    # Related entity
    election = models.ForeignKey(Election, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_display()}: {self.value} at {self.timestamp}"


class ReportTemplate(models.Model):
    """Templates for generating reports"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=30)
    
    # Template configuration
    template_config = models.JSONField()
    css_styles = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ReportSchedule(models.Model):
    """Scheduled report generation"""
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('CUSTOM', 'Custom'),
    ]
    
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=30)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # Schedule configuration
    schedule_config = models.JSONField()
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(blank=True, null=True)
    next_run = models.DateTimeField(blank=True, null=True)
    
    # Recipients
    email_recipients = models.JSONField(default=list)
    
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"


class VoterReceipt(models.Model):
    """Digital receipts for voters after casting votes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Anonymized voter reference (hash of voter_id + salt)
    voter_hash = models.CharField(max_length=64)
    
    # Election details
    election = models.ForeignKey(Election, on_delete=models.PROTECT)
    constituency = models.ForeignKey(Constituency, on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Receipt data
    transaction_hash = models.CharField(max_length=64)
    block_id = models.IntegerField(null=True, blank=True)  # Will be filled when block is mined
    
    # Verification data
    verification_code = models.CharField(max_length=20, unique=True)
    verified = models.BooleanField(default=False)
    
    # Digital signature
    receipt_pdf = models.FileField(upload_to='receipts/', blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['voter_hash']),
            models.Index(fields=['verification_code']),
        ]
    
    def __str__(self):
        return f"Receipt {self.verification_code} for {self.election.name}"
