from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum
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
    ).order_by('voting_start_date')[:5]  # Limit to 5 most recent
    
    # Get voting statistics
    vote_count = VoteRecord.objects.count()
    voter_turnout_pct = 0
    if voter_count > 0:
        voter_turnout_pct = round((vote_count / voter_count) * 100, 1)
    
    # Get blockchain statistics
    blockchain_stats = {
        'total_blocks': Block.objects.count(),
        'total_transactions': VoteTransaction.objects.count(),
        'active_blockchains': Blockchain.objects.filter(election__status__in=['VOTING_OPEN', 'COUNTING']).count(),
    }
    
    # Get party statistics
    party_count = Party.objects.count()
    party_stats = {
        'active_parties': Party.objects.filter(is_active=True).count(),
        'parties_by_recognition': Party.objects.values('recognition_status').annotate(count=Count('id')),
    }
    
    # Get candidate statistics
    candidate_count = Candidate.objects.count()
    candidate_stats = {
        'candidates_by_party': Candidate.objects.values('party__name').annotate(count=Count('id')).order_by('-count')[:5],
    }
    
    # System health check (placeholder values - would be dynamic in production)
    system_health = {
        'blockchain_health': 100,  # percentage
        'server_load': 35,         # percentage
        'security_status': 100     # percentage
    }
    
    context = {
        # Summary counts for stats boxes
        'voter_count': voter_count,
        'election_count': election_count,
        'vote_count': vote_count,
        'party_count': party_count,
        'candidate_count': candidate_count,
        
        # Detailed statistics
        'active_elections': active_elections,
        'voter_turnout_pct': voter_turnout_pct,
        'blockchain_stats': blockchain_stats,
        'party_stats': party_stats,
        'candidate_stats': candidate_stats,
        'states_count': State.objects.count(),
        'constituencies_count': Constituency.objects.count(),
        'system_health': system_health,
    }
    
    return render(request, 'admin/custom_index.html', context)

@staff_member_required
def admin_transactions(request):
    """Admin view for all blockchain vote transactions"""
    transactions = VoteTransaction.objects.select_related('block').order_by('-timestamp')[:200]
    context = {
        'transactions': transactions,
    }
    return render(request, 'admin/transactions.html', context)
