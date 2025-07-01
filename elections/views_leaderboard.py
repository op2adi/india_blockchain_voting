from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, F, Q, ExpressionWrapper, FloatField
from django.db.models.functions import Coalesce
from .models import Election, ElectionResult, CandidateVoteCount, Party, ElectionConstituency
from users.models import State, Constituency

def leaderboard_view(request):
    """
    Display the main leaderboard page with election results.
    """
    # Get active elections
    active_elections = Election.objects.filter(
        status__in=['COUNTING', 'COMPLETED']
    ).order_by('-voting_end_date')
    
    # Get all states for filter
    states = State.objects.all().order_by('name')
    
    # Initialize data structures for the template
    context = {
        'elections': active_elections,
        'states': states,
        'total_votes': 0,
        'voter_turnout': 0,
        'counted_constituencies': 0,
        'total_constituencies': 0,
        'last_updated': timezone.now().strftime('%d-%m-%Y %H:%M:%S'),
        'party_results': [],
        'constituency_results': []
    }
    
    # If there are active elections, get results for the most recent one
    if active_elections.exists():
        selected_election = active_elections.first()
        
        # Get basic election statistics
        election_stats = get_election_statistics(selected_election)
        context.update(election_stats)
        
        # Get party-wise results
        party_results = get_party_results(selected_election)
        context['party_results'] = party_results
        
        # Get constituency results
        constituency_results = ElectionResult.objects.filter(
            election=selected_election
        ).select_related(
            'constituency', 'constituency__state', 'winning_candidate', 'winning_party'
        ).order_by('constituency__name')[:50]  # Limit to 50 constituencies for initial load
        
        context['constituency_results'] = constituency_results
    
    return render(request, 'elections/leaderboard.html', context)

def leaderboard_data_view(request):
    """
    API endpoint to get filtered leaderboard data.
    """
    election_id = request.GET.get('election_id', 'all')
    state_id = request.GET.get('state_id', 'all')
    constituency_id = request.GET.get('constituency_id', 'all')
    
    # Build filter query
    filters = {}
    if election_id != 'all':
        filters['election_id'] = election_id
    
    # Get election results based on filters
    results_query = ElectionResult.objects.filter(**filters)
    
    # Apply additional filters
    if state_id != 'all':
        results_query = results_query.filter(constituency__state_id=state_id)
    
    if constituency_id != 'all':
        results_query = results_query.filter(constituency_id=constituency_id)
    
    # If we have results, prepare the response data
    if results_query.exists():
        # Get the election from the first result
        election = results_query.first().election
        
        # Get basic election statistics with the filters applied
        election_stats = get_election_statistics(election, state_id, constituency_id)
        
        # Get party-wise results with the filters applied
        party_results = get_party_results(election, state_id, constituency_id)
        
        # Get constituency results
        constituency_results_query = results_query.select_related(
            'constituency', 'constituency__state', 'winning_candidate', 'winning_party'
        ).order_by('constituency__name')
        
        # Prepare constituency results data
        constituency_results = []
        for result in constituency_results_query[:100]:  # Limit to 100 for API response
            constituency_results.append({
                'constituency': {
                    'id': result.constituency.id,
                    'name': result.constituency.name,
                    'state': {
                        'id': result.constituency.state.id,
                        'name': result.constituency.state.name,
                    }
                },
                'candidate': {
                    'id': result.winning_candidate.id,
                    'name': result.winning_candidate.name,
                },
                'party': {
                    'id': result.winning_party.id if result.winning_party else None,
                    'name': result.winning_party.name if result.winning_party else 'Independent',
                    'abbreviation': result.winning_party.abbreviation if result.winning_party else 'IND',
                    'color': result.winning_party.party_color if result.winning_party else '#777777',
                },
                'votes_count': result.total_valid_votes,
                'margin': result.winning_margin,
                'status': result.status,
            })
        
        response_data = {
            **election_stats,
            'party_results': party_results,
            'constituency_results': constituency_results,
        }
        
        return JsonResponse(response_data)
    else:
        # Return empty data structure if no results found
        empty_data = {
            'total_votes': 0,
            'voter_turnout': 0,
            'counted_constituencies': 0, 
            'total_constituencies': 0,
            'last_updated': timezone.now().strftime('%d-%m-%Y %H:%M:%S'),
            'party_results': [],
            'constituency_results': []
        }
        return JsonResponse(empty_data)


def get_election_statistics(election, state_id=None, constituency_id=None):
    """
    Helper function to get election statistics with optional filters.
    """
    # Build filter query
    ec_filters = {'election': election}
    if state_id and state_id != 'all':
        ec_filters['constituency__state_id'] = state_id
    
    if constituency_id and constituency_id != 'all':
        ec_filters['constituency_id'] = constituency_id
    
    # Get ElectionConstituency objects for this election with filters
    election_constituencies = ElectionConstituency.objects.filter(**ec_filters)
    
    # Calculate statistics
    total_votes = election_constituencies.aggregate(
        total=Coalesce(Sum('total_votes_cast'), 0)
    )['total']
    
    total_constituencies = election_constituencies.count()
    counted_constituencies = election_constituencies.filter(
        total_votes_cast__gt=0
    ).count()
    
    # Calculate voter turnout
    # For demo, we'll use a simulated number of total registered voters
    total_registered_voters = election_constituencies.aggregate(
        total=Coalesce(Sum(F('total_votes_cast') / F('voter_turnout_percentage') * 100), 0)
    )['total'] or 1  # Avoid division by zero
    
    voter_turnout = round((total_votes / total_registered_voters) * 100, 2) if total_registered_voters > 0 else 0
    
    return {
        'total_votes': total_votes,
        'voter_turnout': voter_turnout,
        'counted_constituencies': counted_constituencies,
        'total_constituencies': total_constituencies,
        'last_updated': timezone.now().strftime('%d-%m-%Y %H:%M:%S'),
    }


def get_party_results(election, state_id=None, constituency_id=None):
    """
    Helper function to get party-wise results with optional filters.
    """
    # Build filter query for CandidateVoteCount
    filters = {'election_result__election': election}
    if state_id and state_id != 'all':
        filters['election_result__constituency__state_id'] = state_id
    
    if constituency_id and constituency_id != 'all':
        filters['election_result__constituency_id'] = constituency_id
    
    # Get party-wise vote counts
    party_votes = CandidateVoteCount.objects.filter(**filters).values(
        'candidate__party'
    ).annotate(
        total_votes=Sum('votes_count'),
        seats_won=Count('id', filter=Q(rank=1)),
        total_constituencies=Count('election_result__constituency', distinct=True)
    ).order_by('-seats_won')
    
    # Calculate total votes
    total_votes = sum(pv['total_votes'] for pv in party_votes)
    total_constituencies = sum(pv['total_constituencies'] for pv in party_votes)
    
    # Prepare party results data
    party_results = []
    for party_vote in party_votes:
        try:
            party = Party.objects.get(id=party_vote['candidate__party']) if party_vote['candidate__party'] else None
            
            # Calculate vote share
            vote_share = round((party_vote['total_votes'] / total_votes) * 100, 2) if total_votes > 0 else 0
            
            # Calculate progress percentage (seats won out of total constituencies)
            progress_percentage = round((party_vote['seats_won'] / total_constituencies) * 100, 2) if total_constituencies > 0 else 0
            
            party_results.append({
                'id': party.id if party else None,
                'name': party.name if party else 'Independent',
                'abbreviation': party.abbreviation if party else 'IND',
                'color': party.party_color if party else '#777777',
                'logo': party.symbol_image.url if party and party.symbol_image else None,
                'seats_won': party_vote['seats_won'],
                'leading_in': 0,  # For simplicity, we're not calculating leading separately
                'vote_share': vote_share,
                'progress_percentage': progress_percentage,
                'is_winner': False  # Will be set to True for the party with most seats
            })
        except Party.DoesNotExist:
            # Handle case where party might have been deleted
            continue
    
    # Sort by seats won and mark the winner
    party_results.sort(key=lambda x: x['seats_won'], reverse=True)
    
    # Mark the party with most seats as winner
    if party_results:
        party_results[0]['is_winner'] = True
    
    return party_results
