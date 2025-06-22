import hashlib
import json
import time
from datetime import datetime
import logging
import uuid

from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import Blockchain, Block, VoteTransaction, BlockchainAuditLog

logger = logging.getLogger(__name__)

class BlockchainVotingService:
    """Service for managing blockchain voting operations"""
    
    @staticmethod
    def create_blockchain_for_election(election):
        """Create a new blockchain for an election"""
        blockchain_name = f"Election-{election.election_id}-Chain"
        genesis_hash = hashlib.sha256(f"genesis-{election.election_id}-{uuid.uuid4()}".encode()).hexdigest()
        
        with transaction.atomic():
            # Create blockchain
            blockchain = Blockchain.objects.create(
                name=blockchain_name,
                genesis_hash=genesis_hash,
                latest_hash=genesis_hash,
                election_id=election.election_id,
                is_active=True,
                difficulty=4  # Configurable difficulty
            )
            
            # Create genesis block
            start_time = time.time()
            genesis_block = Block.objects.create(
                index=0,
                data={"type": "genesis", "election_id": election.election_id, "created_at": timezone.now().isoformat()},
                previous_hash="0",
                hash=genesis_hash,
                nonce=0,
                is_valid=True
            )
            end_time = time.time()
            
            # Log the action
            BlockchainAuditLog.objects.create(
                action="CREATE_BLOCK",
                block=genesis_block,
                blockchain=blockchain,
                actor_type="system",
                actor_id="system",
                details={"block_type": "genesis", "election_id": election.election_id},
                success=True,
                execution_time=end_time - start_time
            )
            
            return blockchain

    @staticmethod
    def record_vote(blockchain, voter_hash, vote_data, ip_address=None, user_agent=None, geolocation=None):
        """Record a vote on the blockchain - can only be called by voting process, not directly by admin"""
        if not blockchain.is_active:
            raise PermissionDenied("This blockchain is not active")
        
        # Add timestamp to vote data
        vote_data["timestamp"] = timezone.now().isoformat()
        
        with transaction.atomic():
            # Start timing
            start_time = time.time()
            
            # Get latest block
            latest_block = blockchain.get_latest_block()
            if not latest_block:
                raise ValueError("Blockchain has no blocks")
            
            # Create new block
            new_block = Block(
                index=blockchain.total_blocks + 1,
                data=vote_data,
                previous_hash=latest_block.hash,
                timestamp=timezone.now(),
                nonce=0
            )
            
            # Mine the block
            new_block.mine_block(blockchain.difficulty)
            new_block.save()
            
            # Update blockchain
            blockchain.latest_hash = new_block.hash
            blockchain.total_blocks += 1
            blockchain.save()
            
            # Create transaction record
            transaction = VoteTransaction.objects.create(
                block=new_block,
                voter_id=voter_hash,  # This is a hash, not the actual voter ID
                transaction_hash=new_block.hash,
                constituency_code=vote_data.get("constituency_id", ""),
                is_confirmed=True,
                ip_address=ip_address,
                user_agent=user_agent,
                geolocation=geolocation
            )
            
            # End timing
            end_time = time.time()
            
            # Log the action
            BlockchainAuditLog.objects.create(
                action="ADD_TRANSACTION",
                block=new_block,
                blockchain=blockchain,
                actor_type="voter",
                actor_id=voter_hash[:8],  # Only use first 8 chars for privacy
                details={"transaction_type": "vote", "election_id": blockchain.election_id},
                success=True,
                execution_time=end_time - start_time
            )
            
            return new_block, transaction
            
    @staticmethod
    def verify_vote(transaction_hash, voter_hash):
        """Verify that a vote belongs to a specific voter"""
        try:
            # Find transaction
            transaction = VoteTransaction.objects.get(transaction_hash=transaction_hash)
            
            # Check if this transaction belongs to this voter
            if transaction.voter_id != voter_hash:
                return False, "Vote not found for this voter"
                
            # Check if transaction's block is valid
            block = transaction.block
            if not block.is_hash_valid():
                return False, "Block hash is invalid"
                
            # Check if block is in the correct position in chain
            blockchain = Blockchain.objects.filter(latest_hash=block.hash).first()
            if not blockchain:
                # Check if it's an older block
                prev_block = Block.objects.filter(previous_hash=block.hash).first()
                if not prev_block:
                    return False, "Block is not part of the blockchain"
            
            return True, "Vote verified successfully"
            
        except VoteTransaction.DoesNotExist:
            return False, "Transaction not found"
        except Exception as e:
            logger.error(f"Error verifying vote: {str(e)}")
            return False, "Error verifying vote"
    
    @staticmethod
    def validate_blockchain(blockchain_id):
        """Validate the entire blockchain"""
        try:
            blockchain = Blockchain.objects.get(id=blockchain_id)
            is_valid = blockchain.is_chain_valid()
            
            # Log validation attempt
            BlockchainAuditLog.objects.create(
                action="VALIDATE_CHAIN",
                blockchain=blockchain,
                actor_type="system",
                actor_id="system",
                details={"is_valid": is_valid},
                success=is_valid,
                error_message="" if is_valid else "Invalid blockchain",
                execution_time=0.0
            )
            
            return is_valid
            
        except Blockchain.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error validating blockchain: {str(e)}")
            return False
