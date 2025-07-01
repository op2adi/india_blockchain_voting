import hashlib
import json
import logging
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

class ConsensusManager:
    """
    Implements consensus protocols for the blockchain network.
    Currently supports:
    - Proof of Work (PoW)
    - Longest chain rule for conflict resolution
    """
    
    @staticmethod
    def validate_block_pow(block, difficulty=None):
        """Validate that a block's hash satisfies the proof of work difficulty requirement"""
        if difficulty is None:
            difficulty = getattr(settings, 'BLOCKCHAIN_DIFFICULTY', 4)
            
        # Check if hash starts with required number of zeros
        target = "0" * difficulty
        return block.hash.startswith(target)
        
    @staticmethod
    def get_chain_work(blocks):
        """
        Calculate the total 'work' in a chain, which is used to determine the 'heaviest' chain.
        In a simple implementation, this is just the length of the chain, but a more
        sophisticated implementation could account for the difficulty of each block.
        """
        return len(blocks)
        
    @staticmethod
    def generate_merkle_root(transaction_hashes):
        """
        Generate a Merkle root from a list of transaction hashes.
        This is used to efficiently verify transactions are included in a block.
        """
        if not transaction_hashes:
            return hashlib.sha256("empty_tree".encode()).hexdigest()
            
        # If odd number of transactions, duplicate the last one
        if len(transaction_hashes) % 2 != 0:
            transaction_hashes.append(transaction_hashes[-1])
            
        # Base case: if only one hash, return it
        if len(transaction_hashes) == 1:
            return transaction_hashes[0]
            
        # Recursively hash pairs of transactions
        new_hashes = []
        for i in range(0, len(transaction_hashes), 2):
            combined = transaction_hashes[i] + transaction_hashes[i+1]
            new_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_hashes.append(new_hash)
            
        # Recursive call with the new level of hashes
        return ConsensusManager.generate_merkle_root(new_hashes)
        
    @staticmethod
    def generate_merkle_proof(transaction_hashes, target_hash):
        """
        Generate a Merkle proof that a transaction is included in a block.
        This returns the minimal set of hashes needed to verify inclusion.
        """
        if not transaction_hashes:
            return []
            
        # If odd number of transactions, duplicate the last one
        if len(transaction_hashes) % 2 != 0:
            transaction_hashes.append(transaction_hashes[-1])
        
        # Find the index of the target hash
        target_index = None
        for i, h in enumerate(transaction_hashes):
            if h == target_hash:
                target_index = i
                break
                
        if target_index is None:
            return []  # Hash not found
            
        # Build the proof
        proof = []
        current_index = target_index
        
        while len(transaction_hashes) > 1:
            # Determine if current_index is left or right in its pair
            is_left = current_index % 2 == 0
            
            # Get the index of the sibling
            sibling_index = current_index - 1 if not is_left else current_index + 1
            
            # If sibling is out of bounds (this can happen if we duplicated the last element)
            if sibling_index >= len(transaction_hashes):
                sibling_index = current_index
                
            # Add the sibling to the proof
            proof.append({
                'position': 'right' if is_left else 'left',
                'hash': transaction_hashes[sibling_index]
            })
            
            # Create the new list of hashes for the next level
            new_hashes = []
            for i in range(0, len(transaction_hashes), 2):
                combined = transaction_hashes[i] + transaction_hashes[i+1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)
                
            # Update current_index for the next level
            current_index = current_index // 2
            
            # Update the list for the next iteration
            transaction_hashes = new_hashes
            
        return proof
        
    @staticmethod
    def verify_merkle_proof(target_hash, proof, merkle_root):
        """
        Verify a Merkle proof that a transaction is included in a block.
        Returns True if the proof is valid, False otherwise.
        """
        current_hash = target_hash
        
        for step in proof:
            if step['position'] == 'right':
                combined = current_hash + step['hash']
            else:
                combined = step['hash'] + current_hash
                
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
            
        return current_hash == merkle_root
