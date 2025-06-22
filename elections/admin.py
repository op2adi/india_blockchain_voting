from django.contrib import admin
from django.utils import timezone
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
import csv
from io import TextIOWrapper
from .models import Party, Candidate, Election, ElectionConstituency

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
    list_display = ('name', 'party', 'election', 'constituency', 'nomination_status', 'is_active')
    list_filter = ('election', 'party', 'constituency', 'nomination_status', 'is_active')
    search_fields = ('name', 'nomination_id')
    actions = ['ban_candidate', 'unban_candidate', 'import_candidates']

    def is_active(self, obj):
        return obj.nomination_status != 'REJECTED'
    is_active.boolean = True
    is_active.short_description = "Active"

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

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'election_type', 'status', 'voting_start_date', 'voting_end_date')
    list_filter = ('status', 'election_type')
    search_fields = ('name', 'election_id')
    readonly_fields = ('blockchain',)
    actions = ['open_voting', 'close_voting', 'start_counting']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'election_type', 'election_id', 'description')
        }),
        ('Geographic Scope', {
            'fields': ('state', 'constituencies')
        }),
        ('Election Timeline', {
            'fields': (
                'announcement_date', 
                'nomination_start_date', 'nomination_end_date',
                'voting_start_date', 'voting_end_date',
                'result_date'
            )
        }),
        ('Status & Configuration', {
            'fields': ('status', 'allow_nota', 'require_photo_id', 'enable_face_verification')
        }),
    )

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

@admin.register(ElectionConstituency)
class ElectionConstituencyAdmin(admin.ModelAdmin):
    list_display = ('election', 'constituency', 'is_active', 'total_votes_cast', 'voter_turnout_percentage')
    list_filter = ('election', 'is_active')
    search_fields = ('constituency__name', 'election__name')

# Import needed for the candidate CSV import
from users.models import Constituency
