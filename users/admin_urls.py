from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.urls import path
from django.db.models import Count, Sum
import csv
import io
import datetime

from users.models import Voter, State, Constituency
from elections.models import Election, VoteRecord, Party, Candidate
from blockchain.models import Block, Blockchain, VoteTransaction

@staff_member_required
def custom_admin_dashboard(request):
    """
    Custom admin dashboard with blockchain stats
    """
    # Get voter statistics
    voter_count = Voter.objects.filter(is_active=True).count()
    
    # Get election statistics
    election_count = Election.objects.count()
    active_elections = Election.objects.filter(
        status__in=['ANNOUNCED', 'NOMINATION_OPEN', 'NOMINATION_CLOSED', 'VOTING_OPEN', 'VOTING_CLOSED', 'COUNTING']
    ).order_by('voting_start')[:5]  # Limit to 5 most recent
    
    # Get blockchain statistics
    blockchain_count = Blockchain.objects.count()
    block_count = Block.objects.count()
    transaction_count = VoteTransaction.objects.count()
    
    context = {
        'title': 'Admin Dashboard',
        'voter_count': voter_count,
        'election_count': election_count,
        'active_elections': active_elections,
        'blockchain_count': blockchain_count,
        'block_count': block_count,
        'transaction_count': transaction_count,
    }
    
    return render(request, 'admin/custom_index.html', context)

@staff_member_required
def import_voters(request):
    """
    Import voters from a CSV file
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # Check if it's a CSV file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('admin:import_voters')
        
        # Process the CSV file
        try:
            # Decode the file
            file_data = csv_file.read().decode('utf-8')
            csv_data = csv.reader(io.StringIO(file_data))
            next(csv_data)  # Skip header row
            
            # Track results
            voters_created = 0
            voters_updated = 0
            errors = []
            
            # Process each row
            for row in csv_data:
                if len(row) < 5:  # Ensure we have at least basic fields
                    errors.append(f"Row has insufficient data: {row}")
                    continue
                
                try:
                    # Extract voter data
                    username = row[0]
                    email = row[1]
                    first_name = row[2]
                    last_name = row[3]
                    voter_id = row[4]
                    
                    # Get optional fields
                    phone = row[5] if len(row) > 5 else ''
                    constituency_name = row[6] if len(row) > 6 else ''
                    state_name = row[7] if len(row) > 7 else ''
                    date_of_birth = row[8] if len(row) > 8 else None
                    
                    # Try to find constituency if provided
                    constituency = None
                    if constituency_name and state_name:
                        try:
                            state = State.objects.get(name__iexact=state_name)
                            constituency = Constituency.objects.get(name__iexact=constituency_name, state=state)
                        except (State.DoesNotExist, Constituency.DoesNotExist):
                            errors.append(f"Constituency or State not found: {constituency_name}, {state_name}")
                            continue
                    
                    # Create or update the voter
                    voter, created = Voter.objects.update_or_create(
                        username=username,
                        defaults={
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'voter_id': voter_id,
                            'phone': phone,
                            'constituency': constituency,
                            'is_active': True,
                        }
                    )
                    
                    # Set date of birth if provided
                    if date_of_birth:
                        try:
                            voter.date_of_birth = datetime.datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                            voter.save()
                        except ValueError:
                            errors.append(f"Invalid date format for {username}: {date_of_birth}. Use YYYY-MM-DD.")
                    
                    # Set a temporary password
                    if created:
                        temp_password = Voter.objects.make_random_password()
                        voter.set_password(temp_password)
                        voter.save()
                        voters_created += 1
                    else:
                        voters_updated += 1
                
                except Exception as e:
                    errors.append(f"Error processing row: {row}. Error: {str(e)}")
            
            # Show summary
            messages.success(
                request, 
                f'Import completed: {voters_created} voters created, {voters_updated} voters updated, {len(errors)} errors'
            )
            
            # If there were errors, show them
            for error in errors[:10]:  # Show only first 10 errors
                messages.warning(request, error)
            
            if len(errors) > 10:
                messages.warning(request, f"... and {len(errors) - 10} more errors")
            
            return redirect('admin:import_voters')
        
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return redirect('admin:import_voters')
    
    # Display the upload form
    return render(request, 'admin/users/import_voters.html', {
        'title': 'Import Voters from CSV',
        'site_header': 'India Blockchain Voting Administration',
    })

@staff_member_required
def download_voter_template(request):
    """
    Download a CSV template for voter import
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="voter_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Username', 'Email', 'First Name', 'Last Name', 'Voter ID', 
        'Phone', 'Constituency', 'State', 'Date of Birth (YYYY-MM-DD)'
    ])
    
    # Add a sample row
    writer.writerow([
        'voter1', 'voter1@example.com', 'John', 'Doe', 'ABC123456',
        '9876543210', 'Mumbai North', 'Maharashtra', '1990-01-01'
    ])
    
    return response

# Add URL patterns for import functionality
urlpatterns = [
    path('dashboard/', custom_admin_dashboard, name='custom_admin_dashboard'),
    path('import-voters/', import_voters, name='import_voters'),
    path('download-voter-template/', download_voter_template, name='download_voter_template'),
]
