import hashlib
import json
import time
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import secrets
import logging

logger = logging.getLogger(__name__)


class CryptographyUtils:
    """Utility class for cryptographic operations"""
    
    @staticmethod
    def generate_key():
        """Generate a new encryption key"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_data(data, key):
        """Encrypt data using Fernet symmetric encryption"""
        f = Fernet(key)
        return f.encrypt(json.dumps(data).encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data, key):
        """Decrypt data using Fernet symmetric encryption"""
        f = Fernet(key)
        decrypted_bytes = f.decrypt(encrypted_data.encode())
        return json.loads(decrypted_bytes.decode())
    
    @staticmethod
    def generate_rsa_keypair():
        """Generate RSA public/private key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    @staticmethod
    def sign_data(data, private_key_pem):
        """Sign data with RSA private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
        )
        
        signature = private_key.sign(
            json.dumps(data, sort_keys=True).encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature.hex()
    
    @staticmethod
    def verify_signature(data, signature_hex, public_key_pem):
        """Verify signature with RSA public key"""
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            signature = bytes.fromhex(signature_hex)
            
            public_key.verify(
                signature,
                json.dumps(data, sort_keys=True).encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class HashUtils:
    """Utility class for hashing operations"""
    
    @staticmethod
    def sha256_hash(data):
        """Calculate SHA-256 hash of data"""
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        elif not isinstance(data, str):
            data = str(data)
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def merkle_root(transactions):
        """Calculate Merkle root of transactions"""
        if not transactions:
            return HashUtils.sha256_hash("")
        
        # Convert all transactions to hashes
        hashes = [HashUtils.sha256_hash(tx) for tx in transactions]
        
        # Build Merkle tree
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last hash if odd number
            
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(HashUtils.sha256_hash(combined))
            
            hashes = new_hashes
        
        return hashes[0]
    
    @staticmethod
    def voter_id_hash(voter_card_number, constituency_code, salt=None):
        """Create a secure hash of voter ID and constituency"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        combined = f"{voter_card_number}:{constituency_code}:{salt}"
        return HashUtils.sha256_hash(combined), salt


class ProofOfWork:
    """Proof of Work implementation"""
    
    @staticmethod
    def mine_block(block_data, previous_hash, difficulty=4):
        """Mine a block using proof of work"""
        nonce = 0
        target = "0" * difficulty
        start_time = time.time()
        
        while True:
            block_string = json.dumps({
                'data': block_data,
                'previous_hash': previous_hash,
                'nonce': nonce,
                'timestamp': datetime.now().isoformat()
            }, sort_keys=True)
            
            block_hash = HashUtils.sha256_hash(block_string)
            
            if block_hash[:difficulty] == target:
                end_time = time.time()
                mining_time = end_time - start_time
                
                logger.info(f"Block mined! Hash: {block_hash}, Nonce: {nonce}, Time: {mining_time:.2f}s")
                
                return {
                    'hash': block_hash,
                    'nonce': nonce,
                    'mining_time': mining_time,
                    'difficulty': difficulty
                }
            
            nonce += 1
            
            # Safety check to prevent infinite loops
            if nonce > 10000000:
                logger.warning(f"Mining taking too long, reducing difficulty")
                difficulty = max(1, difficulty - 1)
                target = "0" * difficulty
                nonce = 0
    
    @staticmethod
    def validate_proof(block_data, previous_hash, nonce, block_hash, difficulty=4):
        """Validate proof of work"""
        target = "0" * difficulty
        
        block_string = json.dumps({
            'data': block_data,
            'previous_hash': previous_hash,
            'nonce': nonce,
            'timestamp': datetime.now().isoformat()
        }, sort_keys=True)
        
        calculated_hash = HashUtils.sha256_hash(block_string)
        
        return (calculated_hash == block_hash and 
                block_hash[:difficulty] == target)


class VoterIdentityUtils:
    """Utilities for voter identity management"""
    
    @staticmethod
    def generate_voter_token(voter_id, election_id, timestamp=None):
        """Generate a unique token for voter authentication"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        token_data = f"{voter_id}:{election_id}:{timestamp}"
        return HashUtils.sha256_hash(token_data)
    
    @staticmethod
    def encrypt_voter_choice(choice_data, voter_key):
        """Encrypt voter's choice data"""
        return CryptographyUtils.encrypt_data(choice_data, voter_key)
    
    @staticmethod
    def create_vote_proof(voter_id, choice_hash, block_hash):
        """Create proof of vote for voter"""
        proof_data = {
            'voter_id_hash': HashUtils.sha256_hash(voter_id),
            'choice_hash': choice_hash,
            'block_hash': block_hash,
            'timestamp': datetime.now().isoformat()
        }
        return HashUtils.sha256_hash(proof_data)


class BlockchainValidator:
    """Blockchain validation utilities"""
    
    @staticmethod
    def validate_block(block, previous_block=None):
        """Validate a single block"""
        # Check if block hash is valid
        calculated_hash = block.calculate_hash()
        if block.hash != calculated_hash:
            return False, "Invalid block hash"
        
        # Check if previous hash matches
        if previous_block and block.previous_hash != previous_block.hash:
            return False, "Previous hash mismatch"
        
        # Check proof of work
        difficulty = 4  # Should come from settings
        if not block.hash.startswith("0" * difficulty):
            return False, "Invalid proof of work"
        
        # Validate block structure
        required_fields = ['index', 'timestamp', 'data', 'previous_hash', 'nonce']
        for field in required_fields:
            if not hasattr(block, field):
                return False, f"Missing required field: {field}"
        
        return True, "Block is valid"
    
    @staticmethod
    def validate_chain(blockchain):
        """Validate entire blockchain"""
        from .models import Block
        
        blocks = Block.objects.filter().order_by('index')
        
        if not blocks.exists():
            return True, "Empty blockchain is valid"
        
        # Validate genesis block
        genesis = blocks.first()
        if genesis.index != 1 or genesis.previous_hash != "0":
            return False, "Invalid genesis block"
        
        # Validate all subsequent blocks
        for i, block in enumerate(blocks[1:], 1):
            previous_block = blocks[i-1]
            is_valid, message = BlockchainValidator.validate_block(block, previous_block)
            
            if not is_valid:
                return False, f"Block {block.index}: {message}"
        
        return True, "Blockchain is valid"
    
    @staticmethod
    def validate_vote_transaction(transaction):
        """Validate a vote transaction"""
        # Check if transaction hash is valid
        expected_hash = HashUtils.sha256_hash({
            'voter_id': transaction.voter_id,
            'block_id': transaction.block.id,
            'timestamp': transaction.timestamp.isoformat()
        })
        
        if transaction.transaction_hash != expected_hash:
            return False, "Invalid transaction hash"
        
        # Check if voter hasn't voted before
        from .models import VoteTransaction
        existing_votes = VoteTransaction.objects.filter(
            voter_id=transaction.voter_id
        ).exclude(id=transaction.id)
        
        if existing_votes.exists():
            return False, "Voter has already voted"
        
        return True, "Transaction is valid"


class GeolocationUtils:
    """Utilities for geolocation verification"""
    
    @staticmethod
    def get_location_from_ip(ip_address):
        """Get location from IP address (mock implementation)"""
        # In production, integrate with a geolocation service like MaxMind
        return {
            'country': 'India',
            'state': 'Unknown',
            'city': 'Unknown',
            'latitude': 0.0,
            'longitude': 0.0,
            'accuracy': 'city'
        }
    
    @staticmethod
    def verify_constituency_location(voter_constituency, voter_location):
        """Verify if voter is in correct constituency (mock implementation)"""
        # In production, implement proper geofencing
        return True  # Allow all for now
    
    @staticmethod
    def log_location_attempt(voter_id, ip_address, location_data):
        """Log location verification attempt"""
        logger.info(f"Location verification for voter {voter_id}: {location_data}")


class AuditUtils:
    """Utilities for audit logging"""
    
    @staticmethod
    def log_blockchain_operation(action, blockchain, actor_type, actor_id, details, success=True, execution_time=0.0, error_message=""):
        """Log blockchain operation for audit"""
        from .models import BlockchainAuditLog
        
        BlockchainAuditLog.objects.create(
            action=action,
            blockchain=blockchain,
            actor_type=actor_type,
            actor_id=actor_id,
            details=details,
            success=success,
            execution_time=execution_time,
            error_message=error_message
        )
    
    @staticmethod
    def generate_audit_report(blockchain, start_date=None, end_date=None):
        """Generate audit report for blockchain"""
        from .models import BlockchainAuditLog
        
        logs = BlockchainAuditLog.objects.filter(blockchain=blockchain)
        
        if start_date:
            logs = logs.filter(timestamp__gte=start_date)
        if end_date:
            logs = logs.filter(timestamp__lte=end_date)
        
        return {
            'total_operations': logs.count(),
            'successful_operations': logs.filter(success=True).count(),
            'failed_operations': logs.filter(success=False).count(),
            'operations_by_type': {
                action[0]: logs.filter(action=action[0]).count()
                for action in BlockchainAuditLog.ACTION_CHOICES
            },
            'operations_by_actor': {},  # Can be expanded
            'logs': list(logs.values())
        }


class MerkleTree:
    """Simple Merkle Tree implementation"""
    def __init__(self, leaves):
        # leaves: list of hex-hash strings
        self.leaves = leaves
        self.levels = [leaves]
        self._build_tree()

    def _build_tree(self):
        current = self.leaves
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i+1] if i+1 < len(current) else left
                combined = left + right
                parent_hash = HashUtils.sha256_hash(combined)
                next_level.append(parent_hash)
            self.levels.append(next_level)
            current = next_level

    def get_root(self):
        return self.levels[-1][0] if self.levels else None

    def get_proof(self, leaf):
        """Return Merkle proof (list of sibling hashes and their position) for a given leaf"""
        proof = []
        try:
            index = self.leaves.index(leaf)
        except ValueError:
            return proof
        for level in self.levels[:-1]:
            sibling_index = index+1 if index % 2 == 0 else index-1
            sibling = level[sibling_index] if sibling_index < len(level) else level[index]
            position = 'right' if index % 2 == 0 else 'left'
            proof.append({'hash': sibling, 'position': position})
            index = index // 2
        return proof
