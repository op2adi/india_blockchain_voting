from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Q, F
from .models import Election, Party, ElectionResult, CandidateVoteCount


def election_results_api(request, election_id):
    """
    API endpoint to get results for a specific election
    """
    election = get_object_or_404(Election, id=election_id)
    
    # Check if the election has results
    if election.status not in ['COUNTING', 'COMPLETED']:
        return JsonResponse({
            'error': 'No results available for this election'
        }, status=400)
    
    # Get party results aggregated
    party_results = []
    parties = Party.objects.filter(
        candidate__election=election
    ).distinct()
    
    for party in parties:
        # Count seats won and leading
        seats_won = CandidateVoteCount.objects.filter(
            election_result__election=election,
            election_result__status='FINAL',
            candidate__party=party,
            rank=1
        ).count()
        
        seats_leading = CandidateVoteCount.objects.filter(
            election_result__election=election,
            election_result__status='COUNTING',
            candidate__party=party,
            rank=1
        ).count()
        
        party_results.append({
            'name': party.name,
            'abbreviation': party.abbreviation,
            'symbol_url': party.symbol_image.url if party.symbol_image else None,
            'color': party.party_color,
            'seats_won': seats_won,
            'seats_leading': seats_leading,
            'total_seats': seats_won + seats_leading
        })
    
    # Sort by total seats in descending order
    party_results.sort(key=lambda x: x['total_seats'], reverse=True)
    
    # Get constituency-wise results
    constituency_results = []
    election_results = ElectionResult.objects.filter(election=election).select_related('constituency', 'winning_candidate', 'winning_party')
    
    for result in election_results:
        # Get the leading candidate (either winning candidate or currently leading one)
        leading_candidate = result.winning_candidate
        leading_party = result.winning_party
        votes = 0
        margin = 0
        
        if leading_candidate:
            # Get votes count for winner
            try:
                winner_votes = CandidateVoteCount.objects.get(
                    election_result=result,
                    candidate=leading_candidate
                ).votes_count
                
                # Get runner-up votes
                runner_up_votes = CandidateVoteCount.objects.filter(
                    election_result=result,
                    rank=2
                ).first()
                
                votes = winner_votes
                margin = winner_votes - runner_up_votes.votes_count if runner_up_votes else 0
            except CandidateVoteCount.DoesNotExist:
                pass
        
        constituency_results.append({
            'name': result.constituency.name,
            'leading_candidate': leading_candidate.name if leading_candidate else "Counting in progress",
            'party': leading_party.abbreviation if leading_party else "",
            'votes': votes,
            'margin': margin,
            'status': result.status
        })
    
    # Prepare response
    response_data = {
        'election': {
            'name': election.name,
            'status': election.get_status_display(),
            'type': election.get_election_type_display()
        },
        'party_results': party_results,
        'constituency_results': constituency_results
    }
    
    return JsonResponse(response_data)
