from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import make_password
import csv
from io import TextIOWrapper
import uuid
from .models import Voter, AdminUser, State, Constituency
from elections.models import Election

# Create a custom admin site
class CustomAdminSite(AdminSite):
    site_header = "India Blockchain Voting Administration"
    site_title = "Voting Admin Portal"
    index_title = "Welcome to the Admin Dashboard"
    index_template = "admin/custom_index.html"
    
    def index(self, request, extra_context=None):
        """Custom index that adds dashboard data"""
        # Get election statistics
        elections = Election.objects.all().order_by('-created_at')
        active_elections = elections.filter(status='VOTING_OPEN').count()
        total_elections = elections.count()
        
        # Get voter statistics
        total_voters = Voter.objects.filter(is_active=True).count()
        
        # Get vote statistics (placeholder - integrate with actual blockchain data)
        votes_cast = 0
        
        # Recent blockchain transactions (placeholder)
        recent_transactions = []
        
        # Base context
        context = {
            'elections': elections[:5],  # Get latest 5 elections
            'total_elections': total_elections,
            'active_elections': active_elections,
            'total_voters': total_voters,
            'votes_cast': votes_cast,
            'recent_transactions': recent_transactions,
        }
        
        # Update with any extra context
        if extra_context:
            context.update(extra_context)
            
        return super().index(request, context)

# Instantiate the custom admin site
django_admin_site = CustomAdminSite(name='custom_admin')

# Admin model classes
class VoterAdmin(admin.ModelAdmin):
    list_display = ('voter_id', 'email', 'first_name', 'last_name', 'constituency', 'is_active', 'is_verified')
    search_fields = ('voter_id', 'email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'is_verified', 'gender', 'state', 'constituency')
    fieldsets = (
        ('Personal Info', {'fields': ('voter_id', 'email', 'first_name', 'last_name', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status', {'fields': ('is_verified', 'verification_date')}),
        ('Demographics', {'fields': ('date_of_birth', 'gender', 'constituency', 'state')}),
        ('Contact', {'fields': ('mobile_number', 'address_line1', 'address_line2', 'city', 'pincode')}),
    )
    actions = ['ban_voters', 'unban_voters', 'verify_voters']
    
    def ban_voters(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} voters banned successfully.")
    ban_voters.short_description = "Ban selected voters"
    
    def unban_voters(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} voters unbanned successfully.")
    unban_voters.short_description = "Unban selected voters"
    
    def verify_voters(self, request, queryset):
        queryset.update(is_verified=True, verification_date=timezone.now())
        self.message_user(request, f"{queryset.count()} voters verified successfully.")
    verify_voters.short_description = "Verify selected voters"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-voters/', self.admin_site.admin_view(self.import_voters_view), name='import-voters'),
        ]
        return custom_urls + urls
        
    def import_voters_view(self, request):
        if request.method == 'POST' and request.FILES.get('voters_csv'):
            try:
                csv_file = request.FILES['voters_csv']
                csv_file = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                reader = csv.DictReader(csv_file)
                
                # Validate required fields
                required_fields = ['voter_id', 'email', 'first_name', 'last_name', 'state', 'constituency']
                for field in required_fields:
                    if field not in reader.fieldnames:
                        self.message_user(
                            request, 
                            f"CSV file must contain columns: {', '.join(required_fields)}", 
                            level=messages.ERROR
                        )
                        return redirect("..")
                
                voters_added = 0
                voters_failed = 0
                errors = []
                
                for row in reader:
                    try:
                        # Check if voter exists
                        if Voter.objects.filter(voter_id=row['voter_id']).exists() or \
                           Voter.objects.filter(email=row['email']).exists():
                            raise ValueError(f"Voter with ID {row['voter_id']} or email {row['email']} already exists")
                        
                        # Find related objects
                        try:
                            state = State.objects.get(name=row['state'])
                        except State.DoesNotExist:
                            raise ValueError(f"State '{row['state']}' does not exist")
                            
                        try:
                            constituency = Constituency.objects.get(name=row['constituency'], state=state)
                        except Constituency.DoesNotExist:
                            raise ValueError(f"Constituency '{row['constituency']}' not found in state '{state.name}'")
                        
                        # Generate a random password or use provided one
                        password = row.get('password', f"PWD{uuid.uuid4().hex[:8]}")
                        
                        # Create date of birth
                        dob = row.get('date_of_birth', '1980-01-01')
                        
                        # Create the voter
                        voter = Voter(
                            voter_id=row['voter_id'],
                            email=row['email'],
                            first_name=row['first_name'],
                            last_name=row['last_name'],
                            state=state,
                            constituency=constituency,
                            password=make_password(password),
                            date_of_birth=dob,
                            gender=row.get('gender', 'M'),
                            mobile_number=row.get('mobile_number', '+91XXXXXXXXXX'),
                            address_line1=row.get('address_line1', 'Default Address'),
                            address_line2=row.get('address_line2', ''),
                            city=row.get('city', state.name),
                            pincode=row.get('pincode', '000000'),
                            is_active=True,
                            is_verified=True,
                            verification_date=timezone.now(),
                            encrypted_voter_card_number='encrypted_placeholder'
                        )
                        voter.save()
                        voters_added += 1
                    except Exception as e:
                        voters_failed += 1
                        errors.append(f"Row {voters_added + voters_failed}: {str(e)}")
                
                # Report results
                if voters_added > 0:
                    self.message_user(request, f"Successfully added {voters_added} voters.")
                
                if voters_failed > 0:
                    self.message_user(
                        request, 
                        f"Failed to add {voters_failed} voters. First few errors: {'; '.join(errors[:5])}",
                        level=messages.WARNING
                    )
                
                return redirect("..")
                
            except Exception as e:
                self.message_user(request, f"Error importing voters: {str(e)}", level=messages.ERROR)
                return redirect("..")
        
        # Get all states and constituencies for reference
        states = State.objects.all()
        constituencies = Constituency.objects.all().select_related('state')
        
        return render(
            request,
            'admin/users/import_voters.html',
            {'states': states, 'constituencies': constituencies}
        )

class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    search_fields = ('user__email', 'user__first_name')

class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

class ConstituencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'state', 'constituency_type')
    list_filter = ('state', 'constituency_type')
    search_fields = ('name', 'code')

# Register models with the custom admin site
django_admin_site.register(Voter, VoterAdmin)
django_admin_site.register(AdminUser, AdminUserAdmin)
django_admin_site.register(State, StateAdmin)
django_admin_site.register(Constituency, ConstituencyAdmin)

# Import and register elections models
from elections.models import Party, Candidate, Election, ElectionConstituency
from elections.admin import PartyAdmin, CandidateAdmin, ElectionAdmin, ElectionConstituencyAdmin

django_admin_site.register(Party, PartyAdmin)
django_admin_site.register(Candidate, CandidateAdmin)
django_admin_site.register(Election, ElectionAdmin)
django_admin_site.register(ElectionConstituency, ElectionConstituencyAdmin)

# Import and register blockchain models
from blockchain.models import Block, Blockchain

# Register blockchain models
django_admin_site.register(Block)
django_admin_site.register(Blockchain)

# Import and register reports models
from reports.models import VotingReport, AuditReport, PerformanceReport

# Register reports models
django_admin_site.register(VotingReport)
django_admin_site.register(AuditReport)
django_admin_site.register(PerformanceReport)

# Standard admin site registration (useful for debugging)
admin.site.register(Voter, VoterAdmin)
admin.site.register(AdminUser, AdminUserAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(Constituency, ConstituencyAdmin)
