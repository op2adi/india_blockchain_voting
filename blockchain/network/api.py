from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from blockchain.models import Block, Blockchain, VoteTransaction
from blockchain.network.node import BlockchainNode
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize blockchain node
node_id = getattr(settings, 'BLOCKCHAIN_NODE_ID', 'node_1')
node_url = getattr(settings, 'BLOCKCHAIN_NODE_URL', 'http://localhost:8000')
known_nodes = getattr(settings, 'BLOCKCHAIN_KNOWN_NODES', [])

blockchain_node = BlockchainNode(node_id, node_url, known_nodes)

class NodeRegisterView(APIView):
    """API endpoint to register a new node in the network"""
    
    def post(self, request):
        try:
            data = request.data
            node_url = data.get('node_url')
            
            if not node_url:
                return Response(
                    {'error': 'Missing node_url parameter'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            success = blockchain_node.register_node(node_url)
            
            if success:
                return Response({
                    'message': f'Node registered: {node_url}',
                    'total_nodes': len(blockchain_node.known_nodes)
                })
            else:
                return Response({
                    'message': f'Node already registered: {node_url}',
                    'total_nodes': len(blockchain_node.known_nodes)
                })
                
        except Exception as e:
            logger.error(f"Error registering node: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NodeListView(APIView):
    """API endpoint to list all known nodes"""
    
    def get(self, request):
        return Response({
            'node_id': blockchain_node.node_id,
            'node_url': blockchain_node.node_url,
            'known_nodes': blockchain_node.known_nodes,
            'total_nodes': len(blockchain_node.known_nodes)
        })

class BlockchainConsensusView(APIView):
    """API endpoint to trigger consensus resolution"""
    
    def get(self, request):
        try:
            replaced = blockchain_node.resolve_conflicts()
            
            if replaced:
                return Response({
                    'message': 'Our chain was replaced with a longer chain',
                    'status': 'chain_replaced'
                })
            else:
                return Response({
                    'message': 'Our chain is authoritative',
                    'status': 'chain_kept'
                })
                
        except Exception as e:
            logger.error(f"Error during consensus resolution: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChainView(APIView):
    """API endpoint to get the full blockchain"""
    
    def get(self, request, blockchain_id):
        try:
            chain_data = blockchain_node.get_blockchain(blockchain_id)
            
            if chain_data:
                return Response(chain_data)
            else:
                return Response(
                    {'error': 'Blockchain not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error getting chain: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class ReceiveBlockView(APIView):
    """API endpoint to receive a new block from another node"""
    
    def post(self, request):
        try:
            block_data = request.data
            
            if not block_data:
                return Response(
                    {'error': 'Missing block data'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            success, message = blockchain_node.receive_block(block_data)
            
            if success:
                return Response({
                    'message': message,
                    'status': 'block_accepted'
                })
            else:
                return Response({
                    'message': message,
                    'status': 'block_rejected'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error receiving block: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NodeStatusView(APIView):
    """API endpoint to get the node status"""
    
    def get(self, request):
        # Get basic blockchain statistics
        blockchains = Blockchain.objects.filter(is_active=True)
        blockchain_stats = []
        
        for blockchain in blockchains:
            blocks = Block.objects.filter(blockchain=blockchain)
            transactions = VoteTransaction.objects.filter(block__blockchain=blockchain)
            
            blockchain_stats.append({
                'id': blockchain.id,
                'name': blockchain.name,
                'total_blocks': blockchain.total_blocks,
                'latest_block_time': blockchain.updated_at.isoformat(),
                'transactions_count': transactions.count(),
            })
            
        return Response({
            'node_id': blockchain_node.node_id,
            'node_url': blockchain_node.node_url,
            'is_running': blockchain_node.is_running,
            'known_nodes': len(blockchain_node.known_nodes),
            'blockchains': blockchain_stats
        })
