from rest_framework import serializers
from .models import VotingReport, AuditReport, PerformanceReport
from elections.serializers import ElectionSerializer
from users.serializers import ConstituencySerializer


class VotingReportSerializer(serializers.ModelSerializer):
    election = ElectionSerializer(read_only=True)
    constituency = ConstituencySerializer(read_only=True)
    
    class Meta:
        model = VotingReport
        fields = ['id', 'election', 'constituency', 'report_type', 'report_data',
                 'pdf_file', 'excel_file', 'generated_by', 'generated_at',
                 'is_public', 'download_count']


class AuditReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditReport
        fields = ['id', 'title', 'report_period_start', 'report_period_end',
                 'report_data', 'pdf_file', 'generated_by', 'generated_at',
                 'is_published', 'download_count']


class PerformanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReport
        fields = ['id', 'title', 'metrics_data', 'charts_data', 'pdf_file',
                 'generated_by', 'generated_at', 'is_public', 'download_count']


class ReportRequestSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    report_type = serializers.ChoiceField(choices=[
        ('CONSTITUENCY_RESULTS', 'Constituency Results'),
        ('PARTY_PERFORMANCE', 'Party Performance'),
        ('VOTER_TURNOUT', 'Voter Turnout'),
        ('BLOCKCHAIN_AUDIT', 'Blockchain Audit'),
        ('SYSTEM_PERFORMANCE', 'System Performance'),
    ])
    election_id = serializers.IntegerField(required=False)
    constituency_id = serializers.IntegerField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    format = serializers.ChoiceField(choices=['PDF', 'EXCEL', 'JSON'], default='PDF')
    include_charts = serializers.BooleanField(default=True)
    is_public = serializers.BooleanField(default=False)
