import json
import logging
import hashlib
import requests
import time
import threading
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from blockchain.models import Block, Blockchain, VoteTransaction, BlockchainAuditLog
from blockchain.utils import ProofOfWork, HashUtils

logger = logging.getLogger(__name__)

class BlockchainNode:
    """
    Represents a node in the blockchain P2P network.
    Each node maintains its own copy of the blockchain and participates in consensus.
    """
    def __init__(self, node_id, node_url, known_nodes=None):
        self.node_id = node_id
        self.node_url = node_url
        self.known_nodes = known_nodes or []
        self.is_running = False
        self.sync_thread = None
        self.mining_thread = None
        
    def start(self):
        """Start the node's operations"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start sync thread
        self.sync_thread = threading.Thread(target=self._sync_blockchain_periodically)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        # Start mining thread if this node is a miner
        if getattr(settings, 'BLOCKCHAIN_NODE_IS_MINER', False):
            self.mining_thread = threading.Thread(target=self._mine_pending_transactions)
            self.mining_thread.daemon = True
            self.mining_thread.start()
            
        logger.info(f"Node {self.node_id} started at {self.node_url}")
        
    def stop(self):
        """Stop the node's operations"""
        self.is_running = False
        logger.info(f"Node {self.node_id} stopped")
        
    def register_node(self, node_url):
        """Register a new node in the network"""
        if node_url not in self.known_nodes and node_url != self.node_url:
            self.known_nodes.append(node_url)
            return True
        return False
        
    def get_blockchain(self, blockchain_id):
        """Get the full blockchain"""
        try:
            blockchain = Blockchain.objects.get(id=blockchain_id)
            blocks = Block.objects.filter(blockchain=blockchain).order_by('index')
            
            chain_data = {
                'blockchain': {
                    'id': blockchain.id,
                    'name': blockchain.name,
                    'difficulty': blockchain.difficulty,
                    'total_blocks': blockchain.total_blocks,
                },
                'blocks': [
                    {
                        'index': block.index,
                        'timestamp': block.timestamp.isoformat(),
                        'data': block.data,
                        'previous_hash': block.previous_hash,
                        'hash': block.hash,
                        'nonce': block.nonce,
                    }
                    for block in blocks
                ]
            }
            
            return chain_data
        except Blockchain.DoesNotExist:
            return None
            
    def broadcast_block(self, block):
        """Broadcast a newly mined block to all known nodes"""
        block_data = {
            'index': block.index,
            'timestamp': block.timestamp.isoformat(),
            'data': block.data,
            'previous_hash': block.previous_hash,
            'hash': block.hash,
            'nonce': block.nonce,
            'blockchain_id': block.blockchain.id
        }
        
        for node_url in self.known_nodes:
            try:
                response = requests.post(
                    f"{node_url}/blockchain/api/receive_block/",
                    json=block_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info(f"Block {block.index} broadcasted to node {node_url}")
                else:
                    logger.warning(f"Failed to broadcast block to node {node_url}: {response.text}")
            except requests.RequestException as e:
                logger.error(f"Error broadcasting block to {node_url}: {str(e)}")
                
    def receive_block(self, block_data):
        """
        Receive a block from another node and validate it before adding to the chain
        Returns True if the block was added, False otherwise
        """
        try:
            blockchain_id = block_data['blockchain_id']
            blockchain = Blockchain.objects.get(id=blockchain_id)
            
            # Check if this block already exists
            existing_block = Block.objects.filter(
                hash=block_data['hash'],
                index=block_data['index']
            ).first()
            
            if existing_block:
                return False, "Block already exists"
                
            # Validate the new block
            previous_block = Block.objects.filter(
                blockchain=blockchain,
                index=block_data['index'] - 1
            ).first()
            
            if not previous_block:
                return False, "Previous block not found"
                
            if previous_block.hash != block_data['previous_hash']:
                return False, "Invalid previous hash"
                
            # Verify proof of work
            is_valid_pow = ProofOfWork.validate_proof(
                block_data['data'],
                block_data['previous_hash'],
                block_data['nonce'],
                block_data['hash'],
                blockchain.difficulty
            )
            
            if not is_valid_pow:
                return False, "Invalid proof of work"
                
            # The block is valid, add it to the chain
            with transaction.atomic():
                new_block = Block.objects.create(
                    index=block_data['index'],
                    timestamp=timezone.now(),
                    data=block_data['data'],
                    previous_hash=block_data['previous_hash'],
                    hash=block_data['hash'],
                    nonce=block_data['nonce'],
                    blockchain=blockchain,
                    is_valid=True
                )
                
                # Update blockchain
                blockchain.latest_hash = new_block.hash
                blockchain.total_blocks = max(blockchain.total_blocks, new_block.index + 1)
                blockchain.save()
                
                # Log this action
                BlockchainAuditLog.objects.create(
                    action="RECEIVE_BLOCK",
                    block=new_block,
                    blockchain=blockchain,
                    actor_type="node",
                    actor_id=self.node_id,
                    details={"source": "p2p_network"},
                    success=True,
                    execution_time=0.0
                )
                
            return True, "Block added successfully"
            
        except Exception as e:
            logger.error(f"Error receiving block: {str(e)}")
            return False, str(e)
            
    def resolve_conflicts(self):
        """
        Consensus algorithm - resolve conflicts by replacing our chain with the longest valid chain
        Returns True if our chain was replaced
        """
        max_length = 0
        new_chain = None
        
        # Get all blockchains we need to check
        blockchains = Blockchain.objects.filter(is_active=True)
        
        for blockchain in blockchains:
            # Check each node for their copy of this blockchain
            for node_url in self.known_nodes:
                try:
                    response = requests.get(
                        f"{node_url}/blockchain/api/chain/{blockchain.id}/",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        node_chain = response.json()
                        node_blocks = node_chain['blocks']
                        
                        # Check if chain is longer and valid
                        if len(node_blocks) > blockchain.total_blocks:
                            # Validate the chain from the other node
                            is_valid = self._validate_chain(node_blocks)
                            
                            if is_valid and len(node_blocks) > max_length:
                                max_length = len(node_blocks)
                                new_chain = node_blocks
                                target_blockchain = blockchain
                                
                except requests.RequestException as e:
                    logger.error(f"Error contacting node {node_url}: {str(e)}")
                    
        # Replace our chain if a longer valid one was found
        if new_chain and max_length > 0:
            with transaction.atomic():
                # Delete all existing blocks
                Block.objects.filter(blockchain=target_blockchain).delete()
                
                # Add new blocks
                for block_data in new_chain:
                    Block.objects.create(
                        index=block_data['index'],
                        timestamp=timezone.parse_datetime(block_data['timestamp']),
                        data=block_data['data'],
                        previous_hash=block_data['previous_hash'],
                        hash=block_data['hash'],
                        nonce=block_data['nonce'],
                        blockchain=target_blockchain,
                        is_valid=True
                    )
                    
                # Update blockchain metadata
                target_blockchain.total_blocks = max_length
                target_blockchain.latest_hash = new_chain[-1]['hash']
                target_blockchain.save()
                
                # Log this action
                BlockchainAuditLog.objects.create(
                    action="RESOLVE_CONFLICTS",
                    blockchain=target_blockchain,
                    actor_type="node",
                    actor_id=self.node_id,
                    details={"replaced_blocks": max_length},
                    success=True,
                    execution_time=0.0
                )
                
            return True
            
        return False
        
    def _validate_chain(self, blocks):
        """Validate a chain of blocks received from another node"""
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i-1]
            
            # Check hash connections
            if current['previous_hash'] != previous['hash']:
                return False
                
            # Validate proof of work
            calculated_hash = HashUtils.calculate_block_hash(
                current['data'],
                current['previous_hash'],
                current['nonce']
            )
            
            if calculated_hash != current['hash']:
                return False
                
        return True
        
    def _sync_blockchain_periodically(self):
        """Periodically synchronize with other nodes"""
        while self.is_running:
            try:
                self.resolve_conflicts()
            except Exception as e:
                logger.error(f"Error during blockchain sync: {str(e)}")
            
            # Sleep for some time before next sync
            time.sleep(getattr(settings, 'BLOCKCHAIN_SYNC_INTERVAL', 30))
            
    def _mine_pending_transactions(self):
        """Mine pending transactions into blocks (if this node is a miner)"""
        while self.is_running:
            try:
                # Get pending transactions
                # This would be implemented based on your transaction pool mechanism
                # For now, we'll just sleep and continue
                pass
            except Exception as e:
                logger.error(f"Error mining pending transactions: {str(e)}")
                
            # Sleep before attempting to mine again
            time.sleep(getattr(settings, 'BLOCKCHAIN_MINING_INTERVAL', 10))
