from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
import logging
import json
from datetime import datetime, timedelta
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from .models import VotingReport, AuditReport, PerformanceReport
from .serializers import (
    VotingReportSerializer, AuditReportSerializer, PerformanceReportSerializer,
    ReportRequestSerializer
)
from elections.models import Election, VoteRecord, Party, Candidate
from blockchain.models import Block, VoteTransaction, BlockchainAuditLog
from users.utils import get_client_ip

logger = logging.getLogger(__name__)


class VotingReportListView(generics.ListCreateAPIView):
    """API endpoint to list and create voting reports"""
    serializer_class = VotingReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = VotingReport.objects.all()
        election_id = self.request.query_params.get('election_id')
        report_type = self.request.query_params.get('report_type')
        is_public = self.request.query_params.get('is_public')
        
        if election_id:
            queryset = queryset.filter(election_id=election_id)
        
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        if is_public:
            queryset = queryset.filter(is_public=True)
        
        return queryset.order_by('-generated_at')


class ReportGenerationView(APIView):
    """API endpoint for generating reports"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Generate a new report",
        request_body=ReportRequestSerializer,
        responses={
            201: VotingReportSerializer(),
            400: "Bad Request - Invalid parameters"
        }
    )
    def post(self, request):
        serializer = ReportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        report_data = serializer.validated_data
        report_type = report_data['report_type']
        
        try:
            # Generate report based on type
            if report_type == 'CONSTITUENCY_RESULTS':
                report = self.generate_constituency_results(report_data)
            elif report_type == 'PARTY_PERFORMANCE':
                report = self.generate_party_performance(report_data)
            elif report_type == 'VOTER_TURNOUT':
                report = self.generate_voter_turnout(report_data)
            elif report_type == 'BLOCKCHAIN_AUDIT':
                report = self.generate_blockchain_audit(report_data)
            elif report_type == 'SYSTEM_PERFORMANCE':
                report = self.generate_system_performance(report_data)
            else:
                return Response(
                    {'error': 'Invalid report type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                VotingReportSerializer(report).data,
                status=status.HTTP_201_CREATED            )
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return Response(
                {'error': 'Failed to generate report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def generate_constituency_results(self, report_data):
        """Generate constituency results report"""
        election_id = report_data.get('election_id')
        constituency_id = report_data.get('constituency_id')
        
        election = Election.objects.get(id=election_id)
        
        # Get vote data
        vote_records = VoteRecord.objects.filter(election=election)
        if constituency_id:
            vote_records = vote_records.filter(constituency_id=constituency_id)
        
        # Aggregate results
        results_data = {
            'election_info': {
                'name': election.name,
                'type': election.election_type,
                'voting_period': f"{election.voting_start_date} to {election.voting_end_date}"
            },
            'constituency_results': self.calculate_constituency_results(vote_records),
            'summary': {
                'total_votes': vote_records.count(),
                'valid_votes': vote_records.filter(vote_type='CANDIDATE').count(),
                'nota_votes': vote_records.filter(vote_type='NOTA').count(),
                'invalid_votes': vote_records.filter(vote_type='INVALID').count()
            }
        }
        
        # Create report
        report = VotingReport.objects.create(
            election=election,
            constituency_id=constituency_id,
            report_type='CONSTITUENCY_RESULTS',
            title=f"Constituency Results - {election.name}",
            report_data=results_data,
            generated_by=request.user.adminuser,
            is_public=report_data.get('is_public', False)
        )
        
        # Generate PDF if requested
        if report_data.get('format') == 'PDF':
            pdf_file = self.generate_pdf_report(report, results_data)
            report.pdf_file = pdf_file
            report.save()
        
        return report
    
    def generate_party_performance(self, report_data, request):
        """Generate party performance report"""
        election_id = report_data.get('election_id')
        election = Election.objects.get(id=election_id)
        
        # Get party performance data
        parties = Party.objects.filter(candidate__election=election).annotate(
            total_votes=Sum('candidate__votes_received'),
            total_candidates=Count('candidate'),
            winning_candidates=Count('candidate', filter=Q(candidate__is_winner=True))
        ).distinct()
        
        party_data = []
        for party in parties:
            party_data.append({
                'name': party.name,
                'abbreviation': party.abbreviation,
                'total_votes': party.total_votes or 0,
                'total_candidates': party.total_candidates,
                'winning_candidates': party.winning_candidates,
                'success_rate': (party.winning_candidates / party.total_candidates * 100) if party.total_candidates > 0 else 0
            })
        
        performance_data = {
            'election_info': {
                'name': election.name,
                'type': election.election_type
            },
            'party_performance': party_data,
            'generated_at': timezone.now().isoformat()
        }
        
        # Create report
        report = VotingReport.objects.create(
            election=election,
            report_type='PARTY_PERFORMANCE',
            title=f"Party Performance - {election.name}",
            report_data=performance_data,
            generated_by=request.user.adminuser,
            is_public=report_data.get('is_public', False)
        )
        
        return report
    
    def generate_voter_turnout(self, report_data, request):
        """Generate voter turnout report"""
        election_id = report_data.get('election_id')
        election = Election.objects.get(id=election_id)
        
        # Calculate turnout by constituency
        turnout_data = []
        for constituency in election.constituencies.all():
            total_voters = constituency.constituency.total_voters
            votes_cast = VoteRecord.objects.filter(
                election=election,
                constituency=constituency.constituency
            ).count()
            
            turnout_percentage = (votes_cast / total_voters * 100) if total_voters > 0 else 0
            
            turnout_data.append({
                'constituency': constituency.constituency.name,
                'total_voters': total_voters,
                'votes_cast': votes_cast,
                'turnout_percentage': round(turnout_percentage, 2)
            })
        
        report_data_obj = {
            'election_info': {
                'name': election.name,
                'type': election.election_type
            },
            'turnout_by_constituency': turnout_data,
            'overall_turnout': {
                'total_eligible_voters': sum(item['total_voters'] for item in turnout_data),
                'total_votes_cast': sum(item['votes_cast'] for item in turnout_data),
                'overall_percentage': sum(item['turnout_percentage'] for item in turnout_data) / len(turnout_data) if turnout_data else 0
            }
        }
        
        # Create report
        report = VotingReport.objects.create(
            election=election,
            report_type='VOTER_TURNOUT',
            title=f"Voter Turnout - {election.name}",
            report_data=report_data_obj,
            generated_by=request.user.adminuser,
            is_public=report_data.get('is_public', False)
        )
        
        return report
    
    def generate_blockchain_audit(self, report_data, request):
        """Generate blockchain audit report"""
        start_date = report_data.get('start_date')
        end_date = report_data.get('end_date')
        
        # Get blockchain audit data
        audit_logs = BlockchainAuditLog.objects.all()
        if start_date:
            audit_logs = audit_logs.filter(timestamp__gte=start_date)
        if end_date:
            audit_logs = audit_logs.filter(timestamp__lte=end_date)
        
        # Analyze audit data
        audit_summary = {
            'total_operations': audit_logs.count(),
            'successful_operations': audit_logs.filter(success=True).count(),
            'failed_operations': audit_logs.filter(success=False).count(),
            'operations_by_type': {},
            'blockchain_integrity': self.check_blockchain_integrity(),
            'security_events': self.analyze_security_events(audit_logs)
        }
        
        # Count operations by type
        for action_choice in BlockchainAuditLog.ACTION_CHOICES:
            action = action_choice[0]
            count = audit_logs.filter(action=action).count()
            if count > 0:
                audit_summary['operations_by_type'][action] = count
        
        # Create audit report
        report = AuditReport.objects.create(
            title=f"Blockchain Audit Report - {timezone.now().strftime('%Y-%m-%d')}",
            report_period_start=start_date or timezone.now() - timedelta(days=30),
            report_period_end=end_date or timezone.now(),
            report_data=audit_summary,
            generated_by=request.user.adminuser,
            is_published=report_data.get('is_public', False)
        )
        
        return report
    
    def generate_system_performance(self, report_data, request):
        """Generate system performance report"""
        start_date = report_data.get('start_date', timezone.now() - timedelta(days=7))
        end_date = report_data.get('end_date', timezone.now())
        
        # Collect performance metrics
        performance_metrics = {
            'time_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'voting_metrics': {
                'total_votes_cast': VoteRecord.objects.filter(
                    voting_timestamp__range=[start_date, end_date]
                ).count(),
                'average_daily_votes': self.calculate_average_daily_votes(start_date, end_date),
                'peak_voting_hours': self.analyze_peak_voting_hours(start_date, end_date)
            },
            'blockchain_metrics': {
                'blocks_created': Block.objects.filter(
                    timestamp__range=[start_date, end_date]
                ).count(),
                'average_block_time': self.calculate_average_block_time(start_date, end_date),
                'transaction_throughput': self.calculate_transaction_throughput(start_date, end_date)
            },
            'system_health': {
                'uptime_percentage': 99.9,  # Mock data
                'error_rate': 0.1,  # Mock data
                'response_time_avg': 250  # Mock data in milliseconds
            }
        }
        
        # Create performance report
        report = PerformanceReport.objects.create(
            title=f"System Performance Report - {timezone.now().strftime('%Y-%m-%d')}",
            metrics_data=performance_metrics,
            generated_by=request.user.adminuser,
            is_public=report_data.get('is_public', False)
        )
        
        return report
    
    def calculate_constituency_results(self, vote_records):
        """Calculate detailed constituency results"""
        # Group votes by constituency and candidate
        results = {}
        
        for vote in vote_records:
            constituency_name = vote.constituency.name
            if constituency_name not in results:
                results[constituency_name] = {
                    'candidates': {},
                    'total_votes': 0,
                    'nota_votes': 0,
                    'invalid_votes': 0
                }
            
            results[constituency_name]['total_votes'] += 1
            
            if vote.vote_type == 'CANDIDATE' and vote.candidate:
                candidate_name = vote.candidate.name
                if candidate_name not in results[constituency_name]['candidates']:
                    results[constituency_name]['candidates'][candidate_name] = {
                        'votes': 0,
                        'party': vote.candidate.party.abbreviation if vote.candidate.party else 'IND'
                    }
                results[constituency_name]['candidates'][candidate_name]['votes'] += 1
            elif vote.vote_type == 'NOTA':
                results[constituency_name]['nota_votes'] += 1
            elif vote.vote_type == 'INVALID':
                results[constituency_name]['invalid_votes'] += 1
        
        return results
    
    def check_blockchain_integrity(self):
        """Check blockchain integrity"""
        # Simplified integrity check
        total_blocks = Block.objects.count()
        valid_blocks = 0
        
        for block in Block.objects.all():
            if block.is_hash_valid():
                valid_blocks += 1
        
        integrity_percentage = (valid_blocks / total_blocks * 100) if total_blocks > 0 else 100
        
        return {
            'total_blocks': total_blocks,
            'valid_blocks': valid_blocks,
            'integrity_percentage': round(integrity_percentage, 2),
            'status': 'HEALTHY' if integrity_percentage > 99 else 'WARNING'
        }
    
    def analyze_security_events(self, audit_logs):
        """Analyze security events from audit logs"""
        security_events = audit_logs.filter(success=False)
        
        return {
            'total_security_events': security_events.count(),
            'failed_operations': list(security_events.values_list('action', flat=True)),
            'suspicious_activities': 0  # Implement proper analysis
        }
    
    def calculate_average_daily_votes(self, start_date, end_date):
        """Calculate average daily votes"""
        total_days = (end_date - start_date).days + 1
        total_votes = VoteRecord.objects.filter(
            voting_timestamp__range=[start_date, end_date]
        ).count()
        
        return total_votes / total_days if total_days > 0 else 0
    
    def analyze_peak_voting_hours(self, start_date, end_date):
        """Analyze peak voting hours"""
        # Simplified analysis
        votes_by_hour = VoteRecord.objects.filter(
            voting_timestamp__range=[start_date, end_date]
        ).extra(
            select={'hour': 'EXTRACT(hour from voting_timestamp)'}
        ).values('hour').annotate(
            vote_count=Count('id')
        ).order_by('-vote_count')[:3]
        
        return list(votes_by_hour)
    
    def calculate_average_block_time(self, start_date, end_date):
        """Calculate average block creation time"""
        blocks = Block.objects.filter(
            timestamp__range=[start_date, end_date]
        ).order_by('timestamp')
        
        if blocks.count() < 2:
            return 0
        
        total_time = 0
        for i in range(1, blocks.count()):
            time_diff = (blocks[i].timestamp - blocks[i-1].timestamp).total_seconds()
            total_time += time_diff
        
        return total_time / (blocks.count() - 1)
    
    def calculate_transaction_throughput(self, start_date, end_date):
        """Calculate transaction throughput"""
        total_transactions = VoteTransaction.objects.filter(
            timestamp__range=[start_date, end_date]
        ).count()
        
        total_hours = (end_date - start_date).total_seconds() / 3600
        
        return total_transactions / total_hours if total_hours > 0 else 0
    
    def generate_pdf_report(self, report, data):
        """Generate PDF report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph(report.title, styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Report content based on type
        if report.report_type == 'CONSTITUENCY_RESULTS':
            self.add_constituency_results_to_pdf(story, data, styles)
        elif report.report_type == 'PARTY_PERFORMANCE':
            self.add_party_performance_to_pdf(story, data, styles)
        elif report.report_type == 'VOTER_TURNOUT':
            self.add_voter_turnout_to_pdf(story, data, styles)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def add_constituency_results_to_pdf(self, story, data, styles):
        """Add constituency results to PDF"""
        # Election info
        election_info = data['election_info']
        story.append(Paragraph(f"Election: {election_info['name']}", styles['Heading2']))
        story.append(Paragraph(f"Type: {election_info['type']}", styles['Normal']))
        story.append(Paragraph(f"Period: {election_info['voting_period']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Summary
        summary = data['summary']
        summary_data = [
            ['Metric', 'Count'],
            ['Total Votes', summary['total_votes']],
            ['Valid Votes', summary['valid_votes']],
            ['NOTA Votes', summary['nota_votes']],
            ['Invalid Votes', summary['invalid_votes']]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 12))
    
    def add_party_performance_to_pdf(self, story, data, styles):
        """Add party performance to PDF"""
        story.append(Paragraph("Party Performance Analysis", styles['Heading2']))
        
        # Party data table
        party_data = data['party_performance']
        table_data = [['Party', 'Abbreviation', 'Total Votes', 'Candidates', 'Won', 'Success Rate']]
        
        for party in party_data:
            table_data.append([
                party['name'],
                party['abbreviation'],
                party['total_votes'],
                party['total_candidates'],
                party['winning_candidates'],
                f"{party['success_rate']:.1f}%"
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    def add_voter_turnout_to_pdf(self, story, data, styles):
        """Add voter turnout to PDF"""
        story.append(Paragraph("Voter Turnout Analysis", styles['Heading2']))
        
        # Overall turnout
        overall = data['overall_turnout']
        story.append(Paragraph(f"Overall Turnout: {overall['overall_percentage']:.1f}%", styles['Normal']))
        story.append(Paragraph(f"Total Eligible Voters: {overall['total_eligible_voters']:,}", styles['Normal']))
        story.append(Paragraph(f"Total Votes Cast: {overall['total_votes_cast']:,}", styles['Normal']))
        story.append(Spacer(1, 12))


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def download_report(request, report_id):
    """Download generated report"""
    try:
        report = VotingReport.objects.get(id=report_id)
        
        # Check if report is public or user has access
        if not report.is_public and not request.user.is_authenticated:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Increment download count
        report.download_count += 1
        report.save()
        
        # Return file response
        if report.pdf_file:
            response = HttpResponse(report.pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
            return response
        elif report.excel_file:
            response = HttpResponse(report.excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{report.title}.xlsx"'
            return response
        else:
            return JsonResponse(report.report_data)
            
    except VotingReport.DoesNotExist:
        return Response(
            {'error': 'Report not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_reports(request):
    """Get list of public reports"""
    reports = VotingReport.objects.filter(is_public=True).order_by('-generated_at')[:20]
    serializer = VotingReportSerializer(reports, many=True)
    return Response(serializer.data)

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views import View
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
# import qrcode  # Commented out until installed
import io
import base64

# Mock APIView for basic functionality
class APIView(View):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

from elections.models import VoteRecord, VoteReceipt

# Report Views
def generate_vote_receipt(request, vote_id):
    """Generate digital receipt for a vote"""
    return render(request, 'reports/receipt.html')

def download_receipt(request, receipt_id):
    """Download receipt PDF"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{receipt_id}.pdf"'
    
    # Create PDF using reportlab (placeholder)
    p = canvas.Canvas(response, pagesize=letter)
    p.drawString(100, 750, f"Vote Receipt: {receipt_id}")
    p.showPage()
    p.save()
    
    return response

def election_report(request, election_id):
    """Generate election report"""
    return render(request, 'reports/election_report.html')

def audit_report(request, blockchain_id):
    """Generate blockchain audit report"""
    return render(request, 'reports/audit_report.html')

# API Views - Basic implementations
class VoteReceiptAPI(APIView):
    """Basic Vote Receipt API"""
    def get(self, request, vote_id):
        return JsonResponse({'message': 'Vote receipt endpoint not fully implemented yet'})

class ElectionStatsAPI(APIView):
    """Basic Election Stats API"""
    def get(self, request, election_id):
        return JsonResponse({'message': 'Election stats endpoint not fully implemented yet'})
