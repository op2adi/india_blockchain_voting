from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg

# Mock APIView for basic functionality
class APIView(View):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

from .models import Block, Blockchain, VoteTransaction, BlockchainAuditLog
from .services import BlockchainVotingService

@login_required
def blockchain_explorer(request):
    """User-facing blockchain explorer view"""
    blockchains = Blockchain.objects.all().order_by('-created_at')
    
    # Paginate blockchains
    paginator = Paginator(blockchains, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get stats
    total_blocks = Block.objects.count()
    total_transactions = VoteTransaction.objects.count()
    
    context = {
        'page_obj': page_obj,
        'total_blockchains': blockchains.count(),
        'total_blocks': total_blocks,
        'total_transactions': total_transactions,
    }
    return render(request, 'blockchain/explorer.html', context)

@login_required
def view_blockchain(request, blockchain_id):
    """View a specific blockchain"""
    blockchain = get_object_or_404(Blockchain, id=blockchain_id)
    
    # Get blocks with pagination
    blocks = Block.objects.filter(blockchain=blockchain).order_by('index')
    paginator = Paginator(blocks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'blockchain': blockchain,
        'page_obj': page_obj,
        'total_blocks': blocks.count(),
    }
    return render(request, 'blockchain/view_blockchain.html', context)

@login_required
def view_block(request, block_id):
    """View a specific block"""
    block = get_object_or_404(Block, id=block_id)
    
    # Get transactions for this block
    transactions = VoteTransaction.objects.filter(block=block)
    
    context = {
        'block': block,
        'transactions': transactions,
        'is_valid': block.is_hash_valid(),
    }
    return render(request, 'blockchain/view_block.html', context)

@login_required
def verify_vote(request):
    """Verify a vote using a transaction hash and voter hash"""
    transaction_hash = request.GET.get('transaction_hash')
    voter_hash = request.GET.get('voter_hash')
    
    if not transaction_hash or not voter_hash:
        return render(request, 'blockchain/verify_vote.html', {
            'verified': None
        })
    
    is_valid, message = BlockchainVotingService.verify_vote(transaction_hash, voter_hash)
    
    context = {
        'verified': is_valid,
        'message': message,
        'transaction_hash': transaction_hash
    }
    return render(request, 'blockchain/verify_vote.html', context)

@staff_member_required
def validate_blockchain(request, blockchain_id):
    """Admin function to validate a blockchain"""
    is_valid = BlockchainVotingService.validate_blockchain(blockchain_id)
    
    return JsonResponse({
        'valid': is_valid,
        'message': 'Blockchain is valid' if is_valid else 'Blockchain is invalid'
    })

# API Views
class BlockListView(APIView):
    """Block List API"""
    def get(self, request):
        blockchain_id = request.GET.get('blockchain_id')
        limit = int(request.GET.get('limit', 100))
        
        blocks_query = Block.objects.all().order_by('-index')
        if blockchain_id:
            blocks_query = blocks_query.filter(blockchain_id=blockchain_id)
        
        blocks = blocks_query[:limit]
        
        block_data = [{
            'id': block.id,
            'index': block.index,
            'timestamp': block.timestamp.isoformat(),
            'hash': block.hash,
            'previous_hash': block.previous_hash,
            'nonce': block.nonce,
            'is_valid': block.is_hash_valid()
        } for block in blocks]
        
        return JsonResponse({
            'blocks': block_data,
            'count': len(block_data)
        })

class BlockDetailView(APIView):
    """Block Detail API"""
    def get(self, request, block_id):
        try:
            block = Block.objects.get(id=block_id)
            
            # Get transactions
            transactions = VoteTransaction.objects.filter(block=block)
            transaction_data = [{
                'id': tx.id,
                'transaction_hash': tx.transaction_hash,
                'timestamp': tx.timestamp.isoformat()
            } for tx in transactions]
            
            block_data = {
                'id': block.id,
                'index': block.index,
                'timestamp': block.timestamp.isoformat(),
                'data': block.data,
                'hash': block.hash,
                'previous_hash': block.previous_hash,
                'nonce': block.nonce,
                'merkle_root': block.merkle_root,
                'is_valid': block.is_hash_valid(),
                'transactions': transaction_data
            }
            
            return JsonResponse(block_data)
        except Block.DoesNotExist:
            return JsonResponse({'error': 'Block not found'}, status=404)

class BlockchainDetailView(APIView):
    """Blockchain Detail API"""
    def get(self, request, pk):
        try:
            blockchain = Blockchain.objects.get(pk=pk)
            
            # Get block count
            block_count = Block.objects.filter(blockchain=blockchain).count()
            
            blockchain_data = {
                'id': blockchain.id,
                'name': blockchain.name,
                'genesis_hash': blockchain.genesis_hash,
                'latest_hash': blockchain.latest_hash,
                'total_blocks': blockchain.total_blocks,
                'block_count': block_count,
                'is_active': blockchain.is_active,
                'created_at': blockchain.created_at.isoformat()
            }
            
            return JsonResponse(blockchain_data)
        except Blockchain.DoesNotExist:
            return JsonResponse({'error': 'Blockchain not found'}, status=404)
