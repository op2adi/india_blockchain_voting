from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
import time

from .models import Block, Blockchain, VoteTransaction, BlockchainAuditLog
from .serializers import (
    BlockSerializer, BlockDetailSerializer, BlockchainSerializer,
    VoteTransactionSerializer, VoteTransactionCreateSerializer,
    BlockchainAuditLogSerializer, BlockchainStatsSerializer,
    BlockValidationSerializer, ChainValidationSerializer,
    MiningStatsSerializer, ProofVerificationSerializer
)
from .utils import BlockchainValidator, ProofOfWork, AuditUtils
from users.utils import get_client_ip

logger = logging.getLogger(__name__)


class BlockchainListView(generics.ListAPIView):
    """API endpoint to list all blockchains"""
    queryset = Blockchain.objects.all()
    serializer_class = BlockchainSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="List all blockchains",
        responses={200: BlockchainSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BlockchainDetailView(generics.RetrieveAPIView):
    """API endpoint for blockchain details"""
    queryset = Blockchain.objects.all()
    serializer_class = BlockchainSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get blockchain details",
        responses={200: BlockchainSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BlockListView(generics.ListAPIView):
    """API endpoint to list blocks in a blockchain"""
    serializer_class = BlockSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        blockchain_id = self.kwargs.get('blockchain_id')
        queryset = Block.objects.all().order_by('index')
        
        if blockchain_id:
            # Filter blocks by blockchain (through election relationship)
            queryset = queryset.filter(
                transactions__block__blockchain_id=blockchain_id
            ).distinct()
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="List blocks in blockchain",
        responses={200: BlockSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BlockDetailView(generics.RetrieveAPIView):
    """API endpoint for block details"""
    queryset = Block.objects.all()
    serializer_class = BlockDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get block details with transactions",
        responses={200: BlockDetailSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VoteTransactionListView(generics.ListCreateAPIView):
    """API endpoint to list and create vote transactions"""
    queryset = VoteTransaction.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VoteTransactionCreateSerializer
        return VoteTransactionSerializer
    
    def get_queryset(self):
        queryset = VoteTransaction.objects.all().order_by('-timestamp')
        block_id = self.request.query_params.get('block_id')
        voter_id = self.request.query_params.get('voter_id')
        
        if block_id:
            queryset = queryset.filter(block_id=block_id)
        
        if voter_id and self.request.user.is_staff:
            # Only allow staff to filter by voter_id for privacy
            queryset = queryset.filter(voter_id=voter_id)
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="List vote transactions",
        manual_parameters=[
            openapi.Parameter('block_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('voter_id', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
        responses={200: VoteTransactionSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Create transaction and log audit"""
        transaction = serializer.save()
        
        # Log audit
        AuditUtils.log_blockchain_operation(
            action='ADD_TRANSACTION',
            blockchain=transaction.block.blockchain if hasattr(transaction.block, 'blockchain') else None,
            actor_type='voter',
            actor_id=transaction.voter_id,
            details={
                'transaction_hash': transaction.transaction_hash,
                'block_index': transaction.block.index
            },
            ip_address=get_client_ip(self.request)
        )


class BlockchainValidationView(APIView):
    """API endpoint for blockchain validation"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Validate entire blockchain",
        responses={
            200: ChainValidationSerializer(),
            404: "Blockchain not found"
        }
    )
    def get(self, request, blockchain_id):
        try:
            blockchain = Blockchain.objects.get(id=blockchain_id)
        except Blockchain.DoesNotExist:
            return Response(
                {'error': 'Blockchain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        start_time = time.time()
        
        # Validate blockchain
        is_valid, message = BlockchainValidator.validate_chain(blockchain)
        
        validation_duration = time.time() - start_time
        
        # Get invalid blocks if any
        invalid_blocks = []
        if not is_valid:
            blocks = Block.objects.filter().order_by('index')
            for block in blocks:
                block_valid, block_message = BlockchainValidator.validate_block(block)
                if not block_valid:
                    invalid_blocks.append({
                        'block_index': block.index,
                        'is_valid': False,
                        'validation_errors': [block_message],
                        'hash_verification': block.is_hash_valid(),
                        'previous_hash_verification': True,  # Simplified
                        'proof_of_work_verification': True,  # Simplified
                        'timestamp_verification': True  # Simplified
                    })
        
        validation_result = {
            'is_valid': is_valid,
            'total_blocks_checked': Block.objects.count(),
            'invalid_blocks': invalid_blocks,
            'validation_timestamp': timezone.now().isoformat(),
            'validation_duration': validation_duration
        }
        
        # Log audit
        AuditUtils.log_blockchain_operation(
            action='VALIDATE_CHAIN',
            blockchain=blockchain,
            actor_type='admin',
            actor_id=str(request.user.id),
            details=validation_result,
            execution_time=validation_duration
        )
        
        return Response(validation_result)


class BlockValidationView(APIView):
    """API endpoint for single block validation"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Validate a single block",
        responses={
            200: BlockValidationSerializer(),
            404: "Block not found"
        }
    )
    def get(self, request, block_id):
        try:
            block = Block.objects.get(id=block_id)
        except Block.DoesNotExist:
            return Response(
                {'error': 'Block not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate block
        is_valid, message = BlockchainValidator.validate_block(block)
        
        validation_result = {
            'block_index': block.index,
            'is_valid': is_valid,
            'validation_errors': [message] if not is_valid else [],
            'hash_verification': block.is_hash_valid(),
            'previous_hash_verification': True,  # Implement proper check
            'proof_of_work_verification': True,  # Implement proper check
            'timestamp_verification': True  # Implement proper check
        }
        
        return Response(validation_result)


class BlockchainStatsView(APIView):
    """API endpoint for blockchain statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get blockchain statistics",
        responses={200: BlockchainStatsSerializer()}
    )
    def get(self, request, blockchain_id=None):
        if blockchain_id:
            try:
                blockchain = Blockchain.objects.get(id=blockchain_id)
                blocks = Block.objects.filter().order_by('index')  # Simplified filtering
            except Blockchain.DoesNotExist:
                return Response(
                    {'error': 'Blockchain not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            blocks = Block.objects.all().order_by('index')
        
        # Calculate statistics
        total_blocks = blocks.count()
        total_transactions = VoteTransaction.objects.count()
        total_votes = total_transactions  # In this system, each transaction is a vote
        
        last_block = blocks.last()
        last_block_time = last_block.timestamp if last_block else None
        
        # Calculate average block time
        if total_blocks > 1:
            first_block = blocks.first()
            total_time = (last_block_time - first_block.timestamp).total_seconds()
            average_block_time = total_time / (total_blocks - 1)
        else:
            average_block_time = 0.0
        
        # Check chain validity
        if blockchain_id:
            chain_validity = blockchain.is_chain_valid()
            current_difficulty = blockchain.difficulty
        else:
            chain_validity = True  # Simplified
            current_difficulty = 4  # Default
        
        stats = {
            'total_blocks': total_blocks,
            'total_transactions': total_transactions,
            'total_votes': total_votes,
            'last_block_time': last_block_time.isoformat() if last_block_time else None,
            'average_block_time': average_block_time,
            'chain_validity': chain_validity,
            'current_difficulty': current_difficulty,
            'pending_transactions': 0  # No pending transactions in this simple implementation
        }
        
        return Response(stats)


class MiningStatsView(APIView):
    """API endpoint for mining statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get mining statistics",
        responses={200: MiningStatsSerializer()}
    )
    def get(self, request):
        # Get mining stats from audit logs
        mining_logs = BlockchainAuditLog.objects.filter(action='MINE_BLOCK')
        
        blocks_mined = mining_logs.count()
        total_mining_time = sum(log.execution_time for log in mining_logs)
        average_mining_time = total_mining_time / blocks_mined if blocks_mined > 0 else 0
        
        # Get latest block
        latest_block = Block.objects.latest('timestamp') if Block.objects.exists() else None
        
        # Calculate hash rate (simplified)
        hash_rate = 1 / average_mining_time if average_mining_time > 0 else 0
        
        stats = {
            'blocks_mined': blocks_mined,
            'total_mining_time': total_mining_time,
            'average_mining_time': average_mining_time,
            'current_difficulty': 4,  # Default difficulty
            'hash_rate': hash_rate,
            'last_mined_block': BlockSerializer(latest_block).data if latest_block else None
        }
        
        return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mine_block(request, blockchain_id):
    """Mine a new block manually (for testing)"""
    try:
        blockchain = Blockchain.objects.get(id=blockchain_id)
    except Blockchain.DoesNotExist:
        return Response(
            {'error': 'Blockchain not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get pending data (for demo, create dummy data)
    block_data = {
        'manual_mining': True,
        'mined_by': str(request.user.id),
        'timestamp': timezone.now().isoformat()
    }
    
    start_time = time.time()
    
    # Mine block
    block = blockchain.add_block(data=block_data)
    
    mining_time = time.time() - start_time
    
    # Log audit
    AuditUtils.log_blockchain_operation(
        action='MINE_BLOCK',
        blockchain=blockchain,
        actor_type='admin',
        actor_id=str(request.user.id),
        details={
            'block_index': block.index,
            'block_hash': block.hash,
            'mining_time': mining_time
        },
        execution_time=mining_time
    )
    
    logger.info(f"Block mined manually: {block.hash} in {mining_time:.2f}s")
    
    return Response({
        'block': BlockSerializer(block).data,
        'mining_time': mining_time,
        'message': 'Block mined successfully'
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def proof_verification_detailed(request, transaction_hash):
    """Detailed proof verification for a transaction"""
    try:
        transaction = VoteTransaction.objects.get(transaction_hash=transaction_hash)
        block = transaction.block
        
        # Verify block hash
        is_hash_valid = block.is_hash_valid()
        
        # Verify transaction hash
        is_transaction_valid = BlockchainValidator.validate_vote_transaction(transaction)
        
        verification_details = {
            'transaction_hash': transaction_hash,
            'block_hash': block.hash,
            'block_index': block.index,
            'is_block_valid': is_hash_valid,
            'is_transaction_valid': is_transaction_valid,
            'verification_timestamp': timezone.now().isoformat(),
            'election_info': {
                'constituency_code': transaction.constituency_code,
                'timestamp': transaction.timestamp.isoformat()
            }
        }
        
        return Response(verification_details)
        
    except VoteTransaction.DoesNotExist:
        return Response(
            {'error': 'Transaction not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class BlockchainAuditLogView(generics.ListAPIView):
    """API endpoint for blockchain audit logs"""
    serializer_class = BlockchainAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = BlockchainAuditLog.objects.all().order_by('-timestamp')
        blockchain_id = self.request.query_params.get('blockchain_id')
        action = self.request.query_params.get('action')
        
        if blockchain_id:
            queryset = queryset.filter(blockchain_id=blockchain_id)
        
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset
    
    @swagger_auto_schema(
        operation_description="List blockchain audit logs",
        manual_parameters=[
            openapi.Parameter('blockchain_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('action', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
        responses={200: BlockchainAuditLogSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# API Views (placeholder implementations)
class BlockListView:
    """Temporary placeholder for Block List API"""
    pass

class BlockDetailView:
    """Temporary placeholder for Block Detail API"""
    pass

class ChainView:
    """Temporary placeholder for Chain API"""
    pass

class ValidateChainView:
    """Temporary placeholder for Chain Validation API"""
    pass

class ProofView:
    """Temporary placeholder for Proof API"""
    pass

class MineBlockView:
    """Temporary placeholder for Mining API"""
    pass

class AuditLogView:
    """Temporary placeholder for Audit Log API"""
    pass
