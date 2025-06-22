from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, F
from django.db import transaction
from .models import Election, Candidate, ElectionConstituency, ElectionResult, CandidateVoteCount, VoteRecord

@staff_member_required
def start_voting_view(request, election_id):
    """Start voting for an election"""
    election = get_object_or_404(Election, pk=election_id)
    
    # Check if election is in the right state to start voting
    if election.status != 'NOMINATION_CLOSED':
        messages.error(request, f"Cannot start voting. Election '{election.name}' is in '{election.get_status_display()}' state.")
        return redirect('admin:index')
    
    # Update election status
    election.status = 'VOTING_OPEN'
    election.voting_start_date = timezone.now()
    election.save()
    
    messages.success(request, f"Voting has been started for '{election.name}'!")
    return redirect('admin:index')

@staff_member_required
def stop_voting_view(request, election_id):
    """Stop voting for an election"""
    election = get_object_or_404(Election, pk=election_id)
    
    # Check if election is in the right state to stop voting
    if election.status != 'VOTING_OPEN':
        messages.error(request, f"Cannot stop voting. Election '{election.name}' is not open for voting.")
        return redirect('admin:index')
    
    # Update election status
    election.status = 'VOTING_CLOSED'
    election.voting_end_date = timezone.now()
    election.save()
    
    messages.success(request, f"Voting has been closed for '{election.name}'!")
    return redirect('admin:index')

@staff_member_required
def start_counting_view(request, election_id):
    """Start counting votes for an election"""
    election = get_object_or_404(Election, pk=election_id)
    
    # Check if election is in the right state to start counting
    if election.status != 'VOTING_CLOSED':
        messages.error(request, f"Cannot start counting. Election '{election.name}' is not closed for voting.")
        return redirect('admin:index')
    
    try:
        with transaction.atomic():
            # Update election status
            election.status = 'COUNTING'
            election.save()
            
            # Count votes for each constituency
            for constituency_link in ElectionConstituency.objects.filter(election=election):
                constituency = constituency_link.constituency
                
                # Get votes for this constituency
                vote_records = VoteRecord.objects.filter(
                    election=election,
                    constituency=constituency,
                    is_valid=True
                )
                
                # Count votes by candidate
                candidate_votes = {}
                nota_votes = 0
                total_votes = vote_records.count()
                total_valid_votes = total_votes  # Assuming all counted votes are valid for now
                
                for vote in vote_records:
                    if vote.candidate:
                        candidate_id = vote.candidate.id
                        if candidate_id in candidate_votes:
                            candidate_votes[candidate_id] += 1
                        else:
                            candidate_votes[candidate_id] = 1
                    else:
                        # NOTA vote
                        nota_votes += 1
                
                # Create result object if doesn't exist
                total_voters = constituency.total_voters
                
                # Sort candidates by votes to determine winner and rankings
                sorted_candidates = sorted(
                    candidate_votes.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                
                # If we have candidates with votes
                if sorted_candidates:
                    winning_candidate_id = sorted_candidates[0][0]
                    winning_candidate = Candidate.objects.get(id=winning_candidate_id)
                    winning_votes = sorted_candidates[0][1]
                    
                    # Calculate margin if there's more than one candidate
                    winning_margin = 0
                    if len(sorted_candidates) > 1:
                        runner_up_votes = sorted_candidates[1][1]
                        winning_margin = winning_votes - runner_up_votes
                    
                    # Calculate victory margin percentage
                    victory_margin_percentage = (winning_margin / total_valid_votes) * 100 if total_valid_votes > 0 else 0
                    
                    # Create or update election result
                    result, created = ElectionResult.objects.update_or_create(
                        election=election,
                        constituency=constituency,
                        defaults={
                            'total_voters': total_voters,
                            'total_votes_cast': total_votes,
                            'total_valid_votes': total_valid_votes,
                            'total_invalid_votes': 0,  # For now, assuming all votes are valid
                            'nota_votes': nota_votes,
                            'voter_turnout_percentage': (total_votes / total_voters) * 100 if total_voters > 0 else 0,
                            'winning_candidate': winning_candidate,
                            'winning_party': winning_candidate.party,
                            'winning_margin': winning_margin,
                            'victory_margin_percentage': victory_margin_percentage,
                            'status': 'PROVISIONAL',
                            'counting_start_time': timezone.now()
                        }
                    )
                    
                    # Create candidate vote counts
                    for rank, (candidate_id, votes) in enumerate(sorted_candidates, 1):
                        candidate = Candidate.objects.get(id=candidate_id)
                        vote_percentage = (votes / total_valid_votes) * 100 if total_valid_votes > 0 else 0
                        
                        CandidateVoteCount.objects.update_or_create(
                            election_result=result,
                            candidate=candidate,
                            defaults={
                                'votes_count': votes,
                                'vote_percentage': vote_percentage,
                                'rank': rank
                            }
                        )
                        
                        # Update candidate model
                        candidate.votes_received = votes
                        candidate.vote_percentage = vote_percentage
                        candidate.rank = rank
                        candidate.is_winner = (rank == 1)
                        candidate.save()
                    
                    # Update constituency election stats
                    constituency_link.total_votes_cast = total_votes
                    constituency_link.total_valid_votes = total_valid_votes
                    constituency_link.total_invalid_votes = 0
                    constituency_link.voter_turnout_percentage = (total_votes / total_voters) * 100 if total_voters > 0 else 0
                    constituency_link.save()
                    
        messages.success(request, f"Vote counting has started for '{election.name}'!")
    except Exception as e:
        messages.error(request, f"Error during counting: {str(e)}")
    
    return redirect('admin:index')

@staff_member_required
def view_results_view(request, election_id):
    """View results for an election"""
    election = get_object_or_404(Election, pk=election_id)
    
    # Get all results for this election
    results = ElectionResult.objects.filter(election=election).select_related(
        'constituency', 'winning_candidate', 'winning_party'
    ).prefetch_related('candidate_votes__candidate__party')
    
    # Get overall statistics
    total_constituencies = results.count()
    total_votes = results.aggregate(total=Sum('total_votes_cast'))['total'] or 0
    total_valid_votes = results.aggregate(total=Sum('total_valid_votes'))['total'] or 0
    nota_votes = results.aggregate(total=Sum('nota_votes'))['total'] or 0
    
    # Get party-wise results
    party_results = {}
    for result in results:
        for vote_count in result.candidate_votes.all():
            party = vote_count.candidate.party
            party_name = party.name if party else "Independent"
            
            if party_name not in party_results:
                party_results[party_name] = {
                    'name': party_name,
                    'seats': 0,
                    'votes': 0,
                    'vote_percentage': 0,
                    'color': party.party_color if party else "#777777"
                }
            
            party_results[party_name]['votes'] += vote_count.votes_count
            if vote_count.candidate.is_winner:
                party_results[party_name]['seats'] += 1
    
    # Calculate vote percentages
    if total_valid_votes > 0:
        for party_name in party_results:
            party_results[party_name]['vote_percentage'] = (party_results[party_name]['votes'] / total_valid_votes) * 100
    
    # Sort by seats won
    sorted_party_results = sorted(
        party_results.values(), 
        key=lambda x: (x['seats'], x['votes']), 
        reverse=True
    )
    
    context = {
        'election': election,
        'results': results,
        'total_constituencies': total_constituencies,
        'total_votes': total_votes,
        'total_valid_votes': total_valid_votes,
        'nota_votes': nota_votes,
        'party_results': sorted_party_results,
        'title': f"Results for {election.name}"
    }
    
    return render(request, 'admin/elections/results.html', context)
