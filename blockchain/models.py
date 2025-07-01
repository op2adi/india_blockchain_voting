import hashlib
import json
from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.conf import settings
from cryptography.fernet import Fernet
from blockchain.network.consensus import ConsensusManager


class Block(models.Model):
    """Individual block in the blockchain"""
    index = models.IntegerField()
    timestamp = models.DateTimeField(default=datetime.now)
    data = models.JSONField()  # Contains vote information
    previous_hash = models.CharField(max_length=64)
    nonce = models.BigIntegerField(default=0)
    hash = models.CharField(max_length=64, unique=True)
    merkle_root = models.CharField(max_length=64, blank=True)
    
    # Validation fields
    is_valid = models.BooleanField(default=True)
    validator_signature = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['index']
        unique_together = ['index', 'hash']
    
    def __str__(self):
        return f"Block #{self.index} - {self.hash[:10]}..."
    
    def calculate_hash(self):
        """Calculate hash for this block"""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'merkle_root': self.merkle_root
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty=4):
        """Mine the block with proof of work"""
        target = "0" * difficulty
        
        # Generate merkle root if we have transactions
        if 'transactions' in self.data:
            transaction_hashes = [tx['hash'] for tx in self.data['transactions']]
            self.merkle_root = ConsensusManager.generate_merkle_root(transaction_hashes)
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def is_hash_valid(self):
        """Verify that the stored hash matches calculated hash"""
        return self.hash == self.calculate_hash()
    
    def generate_merkle_proof(self, transaction_hash):
        """Generate a Merkle proof for a specific transaction in this block"""
        if not self.merkle_root or 'transactions' not in self.data:
            return []
            
        transaction_hashes = [tx['hash'] for tx in self.data['transactions']]
        return ConsensusManager.generate_merkle_proof(transaction_hashes, transaction_hash)


class Blockchain(models.Model):
    """Main blockchain model that manages the chain"""
    name = models.CharField(max_length=100, unique=True)
    genesis_hash = models.CharField(max_length=64)
    latest_hash = models.CharField(max_length=64)
    difficulty = models.IntegerField(default=4)
    total_blocks = models.IntegerField(default=0)
    
    # Election specific fields
    election_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Network information
    network_id = models.CharField(max_length=50, default="main")  # For network identification
    peer_count = models.IntegerField(default=0)  # Number of peers that have this chain
    consensus_hash = models.CharField(max_length=64, blank=True, null=True)  # Used for cross-node validation
    last_validated_by_peers = models.DateTimeField(null=True, blank=True)  # When peers last validated this chain
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Blockchain: {self.name} ({self.total_blocks} blocks)"
    
    def get_latest_block(self):
        """Get the latest block in the chain"""
        return Block.objects.filter(hash=self.latest_hash).first()
    
    def add_block(self, data, voter_id=None, actor_type="voter"):
        """
        Add a new block to the chain
        This method is restricted and can only be called through the proper voting process
        Admin users cannot directly call this method
        """
        if actor_type == "admin":
            raise PermissionDenied("Admin users are not allowed to manually add blocks to the blockchain")
            
        latest_block = self.get_latest_block()
        
        # Add timestamp and actor type for audit
        if isinstance(data, dict):
            data["timestamp"] = datetime.now().isoformat()
            data["actor_type"] = actor_type
            data["node_id"] = getattr(settings, 'BLOCKCHAIN_NODE_ID', 'default_node')
        
        # Calculate transaction hashes for merkle root if this is a vote block
        transaction_hashes = []
        if voter_id and isinstance(data, dict) and data.get("transaction_type") == "vote":
            # Create a hash for this transaction
            transaction_hash = hashlib.sha256(f"{voter_id}:{datetime.now().isoformat()}:{json.dumps(data)}".encode()).hexdigest()
            transaction_hashes.append(transaction_hash)
            data["transaction_hash"] = transaction_hash
        
        new_block = Block(
            index=self.total_blocks + 1,
            data=data,
            previous_hash=latest_block.hash if latest_block else "0",
            timestamp=datetime.now()
        )
        
        # Mine the block using proof of work
        new_block.mine_block(self.difficulty)
        new_block.save()
        
        # Update blockchain
        self.latest_hash = new_block.hash
        self.total_blocks += 1
        self.save()
        
        # Create transaction record
        if voter_id:
            VoteTransaction.objects.create(
                block=new_block,
                voter_id=voter_id,
                transaction_hash=new_block.hash,
                is_confirmed=True
            )
        
        # Log this action for transparency
        BlockchainAuditLog.objects.create(
            action="ADD_BLOCK",
            block=new_block,
            blockchain=self,
            actor_type=actor_type,
            actor_id=voter_id[:8] if voter_id else "system",
            details={"transaction_type": "vote" if voter_id else "system"},
            success=True,
            execution_time=0.0
        )
        
        # Broadcast this block to all peers in the network
        try:
            from blockchain.network.api import blockchain_node
            blockchain_node.broadcast_block(new_block)
        except ImportError:
            # Network module not available
            pass
        
        return new_block
    
    def is_chain_valid(self):
        """Validate the entire blockchain"""
        blocks = Block.objects.filter(blockchain=self).order_by('index')
        
        for i, block in enumerate(blocks):
            # Check if hash is valid
            if not block.is_hash_valid():
                return False
            
            # Check if previous hash matches
            if i > 0 and block.previous_hash != blocks[i-1].hash:
                return False
        
        return True


class VoteTransaction(models.Model):
    """Transaction record for each vote"""
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='transactions')
    voter_id = models.CharField(max_length=255)  # Encrypted voter ID
    transaction_hash = models.CharField(max_length=64, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Vote details (encrypted)
    encrypted_vote_data = models.TextField()
    constituency_code = models.CharField(max_length=10)
    
    # Verification
    is_confirmed = models.BooleanField(default=False)
    confirmation_count = models.IntegerField(default=0)
    
    # Audit trail
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    geolocation = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['voter_id', 'block']
    
    def __str__(self):
        return f"Vote Transaction {self.transaction_hash[:10]}..."
    
    def encrypt_vote_data(self, vote_data, key):
        """Encrypt vote data"""
        f = Fernet(key)
        encrypted_data = f.encrypt(json.dumps(vote_data).encode())
        self.encrypted_vote_data = encrypted_data.decode()
    
    def decrypt_vote_data(self, key):
        """Decrypt vote data"""
        f = Fernet(key)
        decrypted_data = f.decrypt(self.encrypted_vote_data.encode())
        return json.loads(decrypted_data.decode())


class BlockchainAuditLog(models.Model):
    """Audit log for blockchain operations"""
    ACTION_CHOICES = [
        ('CREATE_BLOCK', 'Create Block'),
        ('MINE_BLOCK', 'Mine Block'),
        ('VALIDATE_CHAIN', 'Validate Chain'),
        ('ADD_TRANSACTION', 'Add Transaction'),
        ('VERIFY_VOTE', 'Verify Vote'),
    ]
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    block = models.ForeignKey(Block, on_delete=models.CASCADE, null=True, blank=True)
    blockchain = models.ForeignKey(Blockchain, on_delete=models.CASCADE)
    
    # Actor information
    actor_type = models.CharField(max_length=50)  # voter, admin, system
    actor_id = models.CharField(max_length=255)
    
    # Action details
    details = models.JSONField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Timing
    execution_time = models.FloatField(help_text="Execution time in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} by {self.actor_type} at {self.timestamp}"


class GenesisBlock(models.Model):
    """Special model for genesis block configuration"""
    blockchain = models.OneToOneField(Blockchain, on_delete=models.CASCADE)
    genesis_data = models.JSONField()
    genesis_timestamp = models.DateTimeField()
    creator_signature = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Genesis Block for {self.blockchain.name}"

class Transaction(models.Model):
    """Model for a transaction in the blockchain"""
    blockchain = models.ForeignKey(Blockchain, on_delete=models.CASCADE)
    sender = models.CharField(max_length=255)
    recipient = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction from {self.sender} to {self.recipient} of {self.amount}"