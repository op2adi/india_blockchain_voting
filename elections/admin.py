from django.contrib import admin
from django.utils import timezone
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
import csv
from io import TextIOWrapper
from .models import Party, Candidate, Election, ElectionConstituency, Voter
from .forms import ElectionAdminForm
from users.models import Constituency, State

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'recognition_status', 'is_active')
    search_fields = ('name', 'abbreviation')
    list_filter = ('is_active', 'recognition_status')
    actions = ['ban_party', 'unban_party']

    def ban_party(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} parties banned successfully.")
    ban_party.short_description = "Ban selected parties"

    def unban_party(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} parties unbanned successfully.")
    unban_party.short_description = "Unban selected parties"

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'party', 'election', 'constituency', 'nomination_status')
    list_filter = ('election', 'party', 'constituency', 'nomination_status')
    search_fields = ('name', 'nomination_id')
    actions = ['ban_candidate', 'unban_candidate', 'import_candidates']
    exclude = ('votes_received', 'vote_percentage', 'rank', 'is_winner')

    def get_active_status(self, obj):
        return obj.nomination_status != 'REJECTED'
    get_active_status.boolean = True
    get_active_status.short_description = "Active"

    def ban_candidate(self, request, queryset):
        queryset.update(nomination_status='REJECTED')
        self.message_user(request, f"{queryset.count()} candidates banned successfully.")
    ban_candidate.short_description = "Ban selected candidates"

    def unban_candidate(self, request, queryset):
        queryset.update(nomination_status='ACCEPTED')
        self.message_user(request, f"{queryset.count()} candidates unbanned successfully.")
    unban_candidate.short_description = "Unban selected candidates"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-candidates/', self.admin_site.admin_view(self.import_candidates_view), name='import-candidates'),
            path('download-sample-csv/', self.admin_site.admin_view(self.download_sample_csv), name='download-sample-csv'),
        ]
        return custom_urls + urls

    def import_candidates_view(self, request):
        if request.method == 'POST' and request.FILES.get('candidates_csv'):
            try:
                csv_file = request.FILES['candidates_csv']
                csv_file = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                reader = csv.DictReader(csv_file)
                
                # Validate required fields
                required_fields = ['name', 'party', 'constituency']
                for field in required_fields:
                    if field not in reader.fieldnames:
                        self.message_user(
                            request, 
                            f"CSV file must contain columns: {', '.join(required_fields)}", 
                            level=messages.ERROR
                        )
                        return redirect("..")
                
                candidates_added = 0
                candidates_failed = 0
                errors = []
                
                for row in reader:
                    try:
                        # Find related objects
                        party = Party.objects.get(name=row['party'])
                        constituency = Constituency.objects.get(name=row['constituency'])
                        election = Election.objects.get(id=request.POST.get('election'))
                        
                        # Create the candidate
                        candidate = Candidate(
                            name=row['name'],
                            party=party,
                            constituency=constituency,
                            election=election,
                            father_name=row.get('father_name', 'Not provided'),
                            date_of_birth=row.get('date_of_birth', '1980-01-01'),
                            gender=row.get('gender', 'M'),
                            candidate_number=Candidate.objects.filter(election=election).count() + 1,
                            nomination_id=f"NOM-{election.id}-{timezone.now().strftime('%Y%m%d')}-{candidates_added+1}",
                            nomination_date=timezone.now(),
                            address=row.get('address', 'Address not provided'),
                            nomination_status='ACCEPTED'
                        )
                        candidate.save()
                        candidates_added += 1
                    except Exception as e:
                        candidates_failed += 1
                        errors.append(f"Row {candidates_added + candidates_failed}: {str(e)}")
                
                # Report results
                if candidates_added > 0:
                    self.message_user(request, f"Successfully added {candidates_added} candidates.")
                
                if candidates_failed > 0:
                    self.message_user(
                        request, 
                        f"Failed to add {candidates_failed} candidates. First few errors: {'; '.join(errors[:5])}",
                        level=messages.WARNING
                    )
                
                return redirect("..")
                
            except Exception as e:
                self.message_user(request, f"Error importing candidates: {str(e)}", level=messages.ERROR)
                return redirect("..")
        
        # Get all elections for the dropdown
        elections = Election.objects.all()
        return render(
            request,
            'admin/elections/import_candidates.html',
            {'elections': elections}
        )

    def import_parties_view(self, request):
        if request.method == 'POST' and request.FILES.get('parties_csv'):
            try:
                csv_file = request.FILES['parties_csv']
                csv_file = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                reader = csv.DictReader(csv_file)
                required_fields = ['name', 'abbreviation', 'recognition_status']
                for field in required_fields:
                    if field not in reader.fieldnames:
                        self.message_user(
                            request,
                            f"CSV file must contain columns: {', '.join(required_fields)}",
                            level=messages.ERROR
                        )
                        return redirect("..")
                parties_added = 0
                for row in reader:
                    Party.objects.get_or_create(
                        name=row['name'],
                        abbreviation=row['abbreviation'],
                        recognition_status=row['recognition_status'],
                        defaults={'is_active': True}
                    )
                    parties_added += 1
                self.message_user(request, f"Successfully added {parties_added} parties.")
                return redirect("..")
            except Exception as e:
                self.message_user(request, f"Error importing parties: {str(e)}", level=messages.ERROR)
                return redirect("..")
        return render(request, 'admin/elections/import_parties.html', {})

    def download_sample_csv(self, request):
        sample_type = request.GET.get('type', 'candidates')
        if sample_type == 'parties':
            header = ['name', 'abbreviation', 'recognition_status']
            rows = [
                ['Demo Party', 'DP', 'National'],
                ['Sample Party', 'SP', 'State'],
            ]
            filename = 'sample_parties.csv'
        elif sample_type == 'voters':
            header = ['voter_id', 'name', 'constituency']
            rows = [
                ['VOTER001', 'Amit Kumar', 'Bangalore Central'],
                ['VOTER002', 'Sunita Sharma', 'Mumbai South'],
            ]
            filename = 'sample_voters.csv'
        else:
            header = ['name', 'party', 'constituency', 'father_name', 'date_of_birth', 'gender', 'address']
            rows = [
                ['John Doe', 'Demo Party', 'Constituency 1', 'Father Name', '1980-01-01', 'M', 'Address 1'],
                ['Jane Smith', 'Sample Party', 'Constituency 2', 'Father Name', '1985-05-05', 'F', 'Address 2'],
            ]
            filename = 'sample_candidates.csv'
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        writer = csv.writer(response)
        writer.writerow(header)
        writer.writerows(rows)
        return response

class ElectionConstituencyInline(admin.TabularInline):
    model = ElectionConstituency
    extra = 1
    classes = ['collapse']

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    form = ElectionAdminForm
    list_display = ('name', 'election_type', 'get_status_badge', 'voting_start_date', 'voting_end_date')
    list_filter = ('status', 'election_type')
    search_fields = ('name', 'election_id')
    readonly_fields = ('blockchain',)
    actions = ['open_voting', 'close_voting', 'start_counting']
    inlines = [ElectionConstituencyInline]
    save_on_top = True
    change_form_template = 'admin/elections/election_change_form.html'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'election_type', 'election_id', 'description')
        }),
        ('Geographic Scope', {
            'fields': ('state', 'all_constituencies'),
            'classes': ('wide',)
        }),
        ('Election Timeline', {
            'fields': (
                'announcement_date', 
                'nomination_start_date', 'nomination_end_date',
                'voting_start_date', 'voting_end_date',
                'result_date'
            ),
            'classes': ('wide',),
        }),
        ('Status & Configuration', {
            'fields': ('status', 'allow_nota', 'require_photo_id', 'enable_face_verification', 'blockchain'),
            'classes': ('collapse',),
        }),
    )
    
    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',
            )
        }
        js = ('https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',)
        
    def get_status_badge(self, obj):
        """Display a colored badge for the election status"""
        status_classes = {
            'ANNOUNCED': 'status-announced',
            'NOMINATION_OPEN': 'status-nomination-open',
            'NOMINATION_CLOSED': 'status-nomination-closed',
            'VOTING_OPEN': 'status-voting-open',
            'VOTING_CLOSED': 'status-voting-closed',
            'COUNTING': 'status-counting',
            'COMPLETED': 'status-completed',
            'CANCELLED': 'status-cancelled',
        }
        
        status_class = status_classes.get(obj.status, '')
        readable_status = obj.get_status_display()
        
        return format_html('<span class="status-badge {}">{}</span>', status_class, readable_status)
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'

    def save_model(self, request, obj, form, change):
        """Override save_model to handle the 'all_constituencies' option"""
        super().save_model(request, obj, form, change)
        
        # Process the 'all_constituencies' field
        if form.cleaned_data.get('all_constituencies'):
            # Delete any existing constituency relationships
            ElectionConstituency.objects.filter(election=obj).delete()
            
            # Add all constituencies based on state filter or all if no state specified
            if obj.state:
                constituencies = Constituency.objects.filter(state=obj.state)
            else:
                constituencies = Constituency.objects.all()
                
            for constituency in constituencies:
                ElectionConstituency.objects.create(
                    election=obj,
                    constituency=constituency
                )
            
            self.message_user(request, f"Added all {constituencies.count()} constituencies to this election.")

    def open_voting(self, request, queryset):
        now = timezone.now()
        updated = 0
        for election in queryset:
            if election.status == 'NOMINATION_CLOSED':
                election.status = 'VOTING_OPEN'
                election.voting_start_date = now
                election.save()
                updated += 1
        
        if updated:
            self.message_user(request, f"Voting opened for {updated} election(s).")
        else:
            self.message_user(request, "No elections were updated. Check if they are in 'Nomination Closed' state.", level=messages.WARNING)
    open_voting.short_description = 'Open voting for selected elections'

    def close_voting(self, request, queryset):
        now = timezone.now()
        updated = 0
        for election in queryset:
            if election.status == 'VOTING_OPEN':
                election.status = 'VOTING_CLOSED'
                election.voting_end_date = now
                election.save()
                updated += 1
        
        if updated:
            self.message_user(request, f"Voting closed for {updated} election(s).")
        else:
            self.message_user(request, "No elections were updated. Check if they are in 'Voting Open' state.", level=messages.WARNING)
    close_voting.short_description = 'Close voting for selected elections'
    
    def start_counting(self, request, queryset):
        updated = 0
        for election in queryset:
            if election.status == 'VOTING_CLOSED':
                election.status = 'COUNTING'
                election.save()
                # TODO: Trigger blockchain counting logic
                updated += 1
        
        if updated:
            self.message_user(request, f"Counting started for {updated} election(s).")
        else:
            self.message_user(request, "No elections were updated. Check if they are in 'Voting Closed' state.", level=messages.WARNING)
    start_counting.short_description = 'Start counting for selected elections'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Set default values for new elections
        if obj is None:
            form.base_fields['announcement_date'].initial = timezone.now()
            form.base_fields['nomination_start_date'].initial = timezone.now() + timezone.timedelta(days=1)
            form.base_fields['nomination_end_date'].initial = timezone.now() + timezone.timedelta(days=15)
            form.base_fields['voting_start_date'].initial = timezone.now() + timezone.timedelta(days=30)
            form.base_fields['voting_end_date'].initial = timezone.now() + timezone.timedelta(days=31)
            form.base_fields['result_date'].initial = timezone.now() + timezone.timedelta(days=32)
        
        return form
        
    def get_changeform_initial_data(self, request):
        """
        Provide initial data for the admin form
        """
        return {
            'announcement_date': timezone.now(),
            'nomination_start_date': timezone.now() + timezone.timedelta(days=1),
            'nomination_end_date': timezone.now() + timezone.timedelta(days=15),
            'voting_start_date': timezone.now() + timezone.timedelta(days=30),
            'voting_end_date': timezone.now() + timezone.timedelta(days=31),
            'result_date': timezone.now() + timezone.timedelta(days=32),
        }
        
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Set default values for new elections
        if obj is None:
            form.base_fields['announcement_date'].initial = timezone.now()
            form.base_fields['nomination_start_date'].initial = timezone.now() + timezone.timedelta(days=1)
            form.base_fields['nomination_end_date'].initial = timezone.now() + timezone.timedelta(days=15)
            form.base_fields['voting_start_date'].initial = timezone.now() + timezone.timedelta(days=30)
            form.base_fields['voting_end_date'].initial = timezone.now() + timezone.timedelta(days=31)
            form.base_fields['result_date'].initial = timezone.now() + timezone.timedelta(days=32)
        
        return form
        
    def add_view(self, request, form_url='', extra_context=None):
        """
        Override to add extra context for our template
        """
        extra_context = extra_context or {}
        extra_context['available_states'] = State.objects.all().order_by('name')
        return super().add_view(request, form_url, extra_context=extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Override to add extra context for our template
        """
        extra_context = extra_context or {}
        extra_context['available_states'] = State.objects.all().order_by('name')
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(ElectionConstituency)
class ElectionConstituencyAdmin(admin.ModelAdmin):
    list_display = ('election', 'constituency', 'is_active', 'total_votes_cast', 'voter_turnout_percentage')
    list_filter = ('election', 'is_active')
    search_fields = ('constituency__name', 'election__name')

# Import needed for models
from users.models import Constituency

# Register additional models
from .models import VoteRecord, VoteReceipt, ElectionResult, CandidateVoteCount, ElectionAuditLog

@admin.register(VoteRecord)
class VoteRecordAdmin(admin.ModelAdmin):
    list_display = ('vote_id', 'election', 'constituency', 'vote_type', 'timestamp', 'is_valid')
    search_fields = ('vote_id', 'voter_hash')
    list_filter = ('vote_type', 'is_valid', 'election', 'constituency')
    readonly_fields = ('vote_id', 'timestamp', 'voter_hash', 'transaction_hash')

@admin.register(VoteReceipt)
class VoteReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_id', 'issued_at')
    search_fields = ('receipt_id', 'verification_token')
    readonly_fields = ('receipt_id', 'issued_at')

@admin.register(ElectionResult)
class ElectionResultAdmin(admin.ModelAdmin):
    list_display = ('election', 'constituency', 'status', 'total_votes_cast', 'voter_turnout_percentage')
    search_fields = ('election__name', 'constituency__name')
    list_filter = ('status', 'election')
    readonly_fields = ('result_hash', 'counting_start_time', 'result_declared_time')

@admin.register(CandidateVoteCount)
class CandidateVoteCountAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'election_result', 'votes_count', 'vote_percentage', 'rank')
    search_fields = ('candidate__name',)
    list_filter = ('rank', 'election_result__election')
    readonly_fields = ('created_at',)

@admin.register(ElectionAuditLog)
class ElectionAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'election', 'timestamp', 'actor_type', 'success')
    search_fields = ('action', 'actor_id')
    list_filter = ('action', 'success', 'actor_type')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Set party as a dropdown, not default, and image as optional
        form.base_fields['party'].required = True
        form.base_fields['image'].required = False
        return form
