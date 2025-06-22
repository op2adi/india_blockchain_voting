from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import VotingReport, AuditReport, PerformanceReport

@admin.register(VotingReport)
class VotingReportAdmin(admin.ModelAdmin):
    list_display = ('election', 'constituency', 'report_type', 'created_at')
    list_filter = ('election', 'constituency', 'report_type')
    search_fields = ('election__name', 'constituency__name')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="voting_reports.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Election', 'Constituency', 'Type', 'Created', 'Data'])
        
        for report in queryset:
            writer.writerow([
                report.election.name,
                report.constituency.name if report.constituency else 'All',
                report.get_report_type_display(),
                report.created_at,
                report.report_data
            ])
            
        return response
    export_as_csv.short_description = "Export selected reports to CSV"

@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__voter_id', 'ip_address', 'details')
    readonly_fields = ('timestamp', 'action', 'user', 'ip_address', 'details')

@admin.register(PerformanceReport)
class PerformanceReportAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'metric', 'value')
    list_filter = ('metric', 'timestamp')
    readonly_fields = ('timestamp',)

# Register with the custom admin site
from users.admin import django_admin_site

django_admin_site.register(VotingReport, VotingReportAdmin)
django_admin_site.register(AuditReport, AuditReportAdmin)
django_admin_site.register(PerformanceReport, PerformanceReportAdmin)
