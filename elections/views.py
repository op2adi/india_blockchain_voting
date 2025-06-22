from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Sum, Q, F
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import hashlib
import uuid

from .models import Party, Election, Candidate, VoteRecord, VoteReceipt, ElectionConstituency
from users.models import Voter, Constituency
from blockchain.models import Blockchain, Block, VoteTransaction
from blockchain.services import BlockchainVotingService
from .serializers import PartySerializer, CandidateSerializer, VoteSerializer

# Frontend Views
def home_view(request):
    """Home page view"""
    context = {
        'active_elections': Election.objects.filter(status='VOTING_OPEN').count(),
        'total_voters': Voter.objects.filter(is_active=True).count(),
        'total_constituencies': Constituency.objects.count(),
    }
    return render(request, 'home.html', context)

@login_required
def dashboard_view(request):
    """Voter dashboard"""
    # Default to empty list if no elections found
    available_elections = []
    
    try:
        # Get elections for the user's constituency that are currently open
        if hasattr(request.user, 'constituency'):
            available_elections = Election.objects.filter(
                status='VOTING_OPEN',
                election_constituencies__constituency=request.user.constituency
            ).distinct()
    except Exception as e:
        # Handle any errors silently and continue with empty list
        print(f"Error fetching elections: {str(e)}")
        
    context = {
        'voter': request.user,
        'available_elections': available_elections,
    }
    
    return render(request, 'elections/dashboard.html', context)

@login_required
def view_elections(request):
    """View all available elections for the voter"""
    # Get all elections for the user's constituency
    available_elections = []
    user_votes = {}
    
    try:
        if hasattr(request.user, 'constituency'):
            # Get all elections for this constituency, not just voting_open ones
            available_elections = Election.objects.filter(
                election_constituencies__constituency=request.user.constituency
            ).exclude(status='CANCELLED').distinct()
            
            # Get user's votes for these elections
            user_vote_records = VoteRecord.objects.filter(
                voter_hash__contains=request.user.voter_id, 
                election__in=available_elections
            )
            
            # Create a dictionary of election_id -> vote_id for template use
            for vote in user_vote_records:
                user_votes[vote.election.id] = vote.vote_id
                
    except Exception as e:
        messages.error(request, f"Error loading elections: {str(e)}")
    
    # Add a template filter
    def get_item(dictionary, key):
        return dictionary.get(key)
        
    context = {
        'available_elections': available_elections,
        'user_votes': user_votes,
        'get_item': get_item,
    }
    
    return render(request, 'elections/view_elections.html', context)

@login_required
def vote_view(request, election_id):
    """Voting interface for a specific election"""
    # Get the election
    election = get_object_or_404(Election, id=election_id)
    
    # Check if election is open for voting
    if not election.is_voting_open():
        messages.error(request, "This election is not currently open for voting.")
        return redirect('elections:view_elections')
    
    # Check if user has already voted in this election
    existing_vote = VoteRecord.objects.filter(
        voter_hash__contains=request.user.voter_id, 
        election=election
    ).first()
    
    # Get candidates for the user's constituency in this election
    candidates = Candidate.objects.filter(
        election=election,
        constituency=request.user.constituency,
        nomination_status='ACCEPTED'
    ).select_related('party')
    
    context = {
        'election': election,
        'candidates': candidates,
        'user': request.user,
    }
    
    if existing_vote:
        context['user_vote'] = existing_vote
    
    return render(request, 'elections/vote.html', context)

@login_required
def submit_vote(request, election_id):
    """Process the vote submission"""
    if request.method != 'POST':
        return redirect('elections:vote', election_id=election_id)
    
    election = get_object_or_404(Election, id=election_id)
    
    # Check if election is open
    if not election.is_voting_open():
        messages.error(request, "This election is not currently open for voting.")
        return redirect('elections:view_elections')
    
    # Check if user already voted
    if request.user.has_voted:
        messages.error(request, "You have already cast your vote.")
        # Find the user's vote record
        vote_record = VoteRecord.objects.filter(
            voter_hash__contains=request.user.voter_id, 
            election=election
        ).first()
        if vote_record:
            return redirect('elections:view_receipt', vote_id=vote_record.vote_id)
        return redirect('elections:view_elections')
    
    # Get the candidate selection
    candidate_id = request.POST.get('candidate_id')
    
    # Handle NOTA option
    if candidate_id == 'NOTA':
        candidate = None  # NOTA vote
    else:
        try:
            candidate = Candidate.objects.get(id=candidate_id, election=election)
        except Candidate.DoesNotExist:
            messages.error(request, "Invalid candidate selection.")
            return redirect('elections:vote', election_id=election_id)
    
    try:        # Create or use existing blockchain
        if not election.blockchain:
            # Create blockchain if it doesn't exist
            blockchain = BlockchainVotingService.create_blockchain_for_election(election)
            election.blockchain = blockchain
            election.save()
        else:
            blockchain = election.blockchain
        
        # Create vote data
        vote_data = {
            "election_id": election.election_id,
            "constituency_id": request.user.constituency.id,
            "candidate_id": candidate.id if candidate else "NOTA",
        }
        
        # Create a voter hash that doesn't expose identity
        voter_hash = hashlib.sha256(f"{request.user.voter_id}-{election.election_id}-{uuid.uuid4()}".encode()).hexdigest()
        
        # Get IP and user agent if available
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')
        
        # Add block to blockchain
        block, transaction = BlockchainVotingService.record_vote(
            blockchain, 
            voter_hash, 
            vote_data, 
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Record the vote
        vote_record = VoteRecord.objects.create(
            election=election,
            constituency=request.user.constituency,
            candidate=candidate,
            block=block,
            transaction_hash=block.hash,
            voter_hash=voter_hash,
            is_valid=True
        )
        
        # Create receipt
        verification_hash = hashlib.sha256(f"{vote_record.vote_id}-{block.hash}".encode()).hexdigest()
        receipt = VoteReceipt.objects.create(
            vote_record=vote_record,
            verification_hash=verification_hash,
            verification_token=uuid.uuid4().hex
        )
        
        # Generate QR code for receipt
        receipt.generate_qr_code()
        
        # Update voter status
        request.user.has_voted = True
        request.user.vote_count += 1
        request.user.last_voted_at = timezone.now()
        request.user.save()
        
        # Update candidate vote count if not NOTA
        if candidate:
            candidate.votes_received += 1
            candidate.save()
            
        # Update constituency stats
        constituency_election = ElectionConstituency.objects.get(
            election=election, 
            constituency=request.user.constituency
        )
        constituency_election.total_votes_cast += 1
        constituency_election.save()
        
        messages.success(request, "Your vote has been successfully recorded.")
        return redirect('elections:view_receipt', vote_id=vote_record.vote_id)
    
    except Exception as e:
        messages.error(request, f"Error processing your vote: {str(e)}")
        return redirect('elections:vote', election_id=election_id)

@login_required
def view_receipt(request, vote_id):
    """View the digital receipt for a vote"""
    vote_record = get_object_or_404(VoteRecord, vote_id=vote_id)
    
    # Security check - user should only see their own receipt
    # The voter_hash contains a hash of the voter ID, so we check if the current user's ID is in the hash
    if request.user.voter_id not in vote_record.voter_hash:
        messages.error(request, "You don't have permission to view this receipt.")
        return redirect('elections:view_elections')
    
    receipt = get_object_or_404(VoteReceipt, vote_record=vote_record)
    
    context = {
        'vote_record': vote_record,
        'receipt': receipt
    }
    
    return render(request, 'elections/vote_receipt.html', context)

def leaderboard_view(request):
    """Public leaderboard"""
    elections = Election.objects.filter(
        Q(status='COMPLETED') | Q(status='COUNTING')
    ).order_by('-result_date')[:5]
    
    context = {
        'elections': elections
    }
    
    return render(request, 'elections/leaderboard.html', context)

def results_view(request, election_id=None):
    """Election results"""
    if election_id:
        election = get_object_or_404(Election, id=election_id)
        # Check if results are available
        if election.status not in ['COMPLETED', 'COUNTING']:
            messages.info(request, "Results are not available yet for this election.")
            return redirect('elections:view_elections')
            
        # Get results for this election
        results = election.results.all().prefetch_related('candidate_votes__candidate__party')
        
        context = {
            'election': election,
            'results': results,
        }
    else:
        # Show list of elections with available results
        elections_with_results = Election.objects.filter(
            Q(status='COMPLETED') | Q(status='COUNTING')
        ).order_by('-result_date')
        
        context = {
            'elections_with_results': elections_with_results
        }
    
    return render(request, 'elections/results.html', context)

# API Views - Basic implementations  
class PartyListView(APIView):
    """Basic Party API"""
    def get(self, request):
        parties = Party.objects.filter(is_active=True)
        serializer = PartySerializer(parties, many=True)
        return Response(serializer.data)

class CandidateListView(APIView):
    """Basic Candidate API"""
    def get(self, request):
        constituency_id = request.query_params.get('constituency')
        candidates = Candidate.objects.filter(is_active=True)
        if constituency_id:
            candidates = candidates.filter(constituency_id=constituency_id)
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data)

class CastVoteView(APIView):
    """Basic Vote API"""
    def post(self, request):
        serializer = VoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            election = Election.objects.get(id=data['election_id'])
            if not election.can_accept_votes():
                raise Exception('Voting not open')
            # TODO: build block and record vote
            return Response({'message': 'Vote recorded (stub)'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class LeaderboardView(APIView):
    """API endpoint for election leaderboards"""
    def get(self, request):
        # Get ongoing and completed elections
        elections = Election.objects.filter(
            status__in=['VOTING_OPEN', 'VOTING_CLOSED', 'COUNTING', 'COMPLETED']
        ).order_by('-created_at')[:5]
        
        data = []
        for election in elections:
            # Get top candidates for this election
            candidates = Candidate.objects.filter(
                election=election
            ).order_by('-votes_received')[:5]
            
            election_data = {
                'id': election.id,
                'name': election.name,
                'type': election.get_election_type_display(),
                'status': election.get_status_display(),
                'top_candidates': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'party': c.party.name if c.party else 'Independent',
                        'votes': c.votes_received,
                        'constituency': c.constituency.name
                    } for c in candidates
                ]
            }
            data.append(election_data)
            
        return Response(data)

class ResultsView(APIView):
    """API endpoint for election results"""
    def get(self, request, election_id):
        try:
            election = Election.objects.get(id=election_id)
            
            # Check if results are available
            if election.status not in ['COMPLETED', 'COUNTING']:
                return Response(
                    {'error': 'Results are not available for this election yet'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get results for this election
            results = []
            for election_result in election.results.all().select_related('constituency', 'winning_candidate', 'winning_party'):
                # Get candidate votes
                candidate_votes = []
                for vote_count in election_result.candidate_votes.all().select_related('candidate', 'candidate__party'):
                    candidate_votes.append({
                        'candidate_id': vote_count.candidate.id,
                        'name': vote_count.candidate.name,
                        'party': vote_count.candidate.party.name if vote_count.candidate.party else 'Independent',
                        'votes': vote_count.votes_count,
                        'vote_percentage': vote_count.vote_percentage,
                        'rank': vote_count.rank
                    })
                
                result_data = {
                    'constituency': {
                        'id': election_result.constituency.id,
                        'name': election_result.constituency.name
                    },
                    'winner': {
                        'name': election_result.winning_candidate.name,
                        'party': election_result.winning_party.name if election_result.winning_party else 'Independent',
                        'votes': election_result.winning_candidate.votes_received
                    },
                    'stats': {
                        'total_voters': election_result.total_voters,
                        'total_votes_cast': election_result.total_votes_cast,
                        'voter_turnout_percentage': election_result.voter_turnout_percentage,
                        'nota_votes': election_result.nota_votes
                    },
                    'candidate_votes': candidate_votes,
                    'status': election_result.get_status_display()
                }
                results.append(result_data)
                
            return Response({
                'election': {
                    'id': election.id,
                    'name': election.name,
                    'type': election.get_election_type_display(),
                    'status': election.get_status_display()
                },
                'results': results
            })
            
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class LeaderboardView(APIView):
    """Basic Leaderboard API"""
    def get(self, request):
        # TODO: aggregate votes per party
        return Response({'leaderboard': []})

class ResultsView(APIView):
    """Basic Results API"""
    def get(self, request, election_id):
        return JsonResponse({'message': 'Results endpoint not fully implemented yet'})
