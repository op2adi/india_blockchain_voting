from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from users.models import Voter
from elections.models import Election, VoteRecord
from blockchain.models import Block

@staff_member_required
def custom_admin_dashboard(request):
    """
    Custom admin dashboard with blockchain stats
    """
    context = {
        'voter_count': Voter.objects.filter(is_active=True).count(),
        'active_election_count': Election.objects.filter(status='VOTING_OPEN').count(),
        'vote_count': VoteRecord.objects.count(),
        'block_count': Block.objects.count(),
        'current_election': Election.objects.filter(status='VOTING_OPEN').first(),
        'recent_blocks': Block.objects.all().order_by('-timestamp')[:5],
    }
    
    return render(request, 'admin/custom_index.html', context)
