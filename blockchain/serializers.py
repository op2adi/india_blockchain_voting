from rest_framework import serializers
from .models import Block, Blockchain, VoteTransaction, BlockchainAuditLog, GenesisBlock
from django.utils import timezone


class BlockSerializer(serializers.ModelSerializer):
    """Serializer for blockchain blocks"""
    is_hash_valid = serializers.SerializerMethodField()
    transactions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Block
        fields = ['id', 'index', 'timestamp', 'data', 'previous_hash', 'nonce',
                 'hash', 'merkle_root', 'is_valid', 'validator_signature',
                 'is_hash_valid', 'transactions_count', 'created_at']
        read_only_fields = ['hash', 'created_at']
    
    def get_is_hash_valid(self, obj):
        """Check if block hash is valid"""
        return obj.is_hash_valid()
    
    def get_transactions_count(self, obj):
        """Get number of transactions in this block"""
        return obj.transactions.count()


class BlockDetailSerializer(BlockSerializer):
    """Detailed block serializer with transactions"""
    transactions = serializers.SerializerMethodField()
    
    class Meta(BlockSerializer.Meta):
        fields = BlockSerializer.Meta.fields + ['transactions']
    
    def get_transactions(self, obj):
        """Get all transactions in this block"""
        transactions = VoteTransaction.objects.filter(block=obj)
        return VoteTransactionSerializer(transactions, many=True).data


class BlockchainSerializer(serializers.ModelSerializer):
    """Serializer for blockchain"""
    latest_block = serializers.SerializerMethodField()
    is_chain_valid = serializers.SerializerMethodField()
    blocks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Blockchain
        fields = ['id', 'name', 'genesis_hash', 'latest_hash', 'difficulty',
                 'total_blocks', 'election_id', 'is_active', 'latest_block',
                 'is_chain_valid', 'blocks_count', 'created_at']
        read_only_fields = ['genesis_hash', 'latest_hash', 'total_blocks', 'created_at']
    
    def get_latest_block(self, obj):
        """Get the latest block in the chain"""
        latest_block = obj.get_latest_block()
        if latest_block:
            return BlockSerializer(latest_block).data
        return None
    
    def get_is_chain_valid(self, obj):
        """Check if the entire blockchain is valid"""
        return obj.is_chain_valid()
    
    def get_blocks_count(self, obj):
        """Get actual count of blocks"""
        return Block.objects.filter().count()


class VoteTransactionSerializer(serializers.ModelSerializer):
    """Serializer for vote transactions"""
    block = BlockSerializer(read_only=True)
    is_confirmed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = VoteTransaction
        fields = ['id', 'block', 'voter_id', 'transaction_hash', 'timestamp',
                 'encrypted_vote_data', 'constituency_code', 'is_confirmed',
                 'confirmation_count', 'ip_address', 'user_agent', 'geolocation']
        read_only_fields = ['transaction_hash', 'timestamp', 'is_confirmed']


class VoteTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating vote transactions"""
    vote_data = serializers.JSONField(write_only=True)
    encryption_key = serializers.CharField(write_only=True)
    
    class Meta:
        model = VoteTransaction
        fields = ['voter_id', 'constituency_code', 'vote_data', 'encryption_key',
                 'ip_address', 'user_agent', 'geolocation']
    
    def validate(self, attrs):
        """Validate transaction data"""
        # Check if voter hasn't already voted
        voter_id = attrs['voter_id']
        existing_transaction = VoteTransaction.objects.filter(voter_id=voter_id).first()
        if existing_transaction:
            raise serializers.ValidationError("Voter has already cast a vote")
        
        return attrs
    
    def create(self, validated_data):
        """Create new vote transaction and add to blockchain"""
        vote_data = validated_data.pop('vote_data')
        encryption_key = validated_data.pop('encryption_key')
        
        # Create transaction instance
        transaction = VoteTransaction(**validated_data)
        
        # Encrypt vote data
        transaction.encrypt_vote_data(vote_data, encryption_key.encode())
        
        # Get or create blockchain for current election
        blockchain, _ = Blockchain.objects.get_or_create(
            election_id=vote_data.get('election_id', 'default'),
            defaults={'name': f"Election_{vote_data.get('election_id', 'default')}"}
        )
        
        # Add transaction to blockchain
        block = blockchain.add_block(
            data={
                'voter_id': transaction.voter_id,
                'constituency_code': transaction.constituency_code,
                'timestamp': timezone.now().isoformat(),
                'transaction_type': 'VOTE'
            },
            voter_id=transaction.voter_id
        )
        
        # Associate transaction with block
        transaction.block = block
        transaction.transaction_hash = block.hash
        transaction.save()
        
        return transaction


class BlockchainAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for blockchain audit logs"""
    block = BlockSerializer(read_only=True)
    blockchain = BlockchainSerializer(read_only=True)
    
    class Meta:
        model = BlockchainAuditLog
        fields = ['id', 'action', 'block', 'blockchain', 'actor_type', 'actor_id',
                 'details', 'success', 'error_message', 'execution_time', 'timestamp']
        read_only_fields = ['timestamp']


class GenesisBlockSerializer(serializers.ModelSerializer):
    """Serializer for genesis block"""
    blockchain = BlockchainSerializer(read_only=True)
    
    class Meta:
        model = GenesisBlock
        fields = ['id', 'blockchain', 'genesis_data', 'genesis_timestamp',
                 'creator_signature', 'created_at']
        read_only_fields = ['created_at']


class BlockchainStatsSerializer(serializers.Serializer):
    """Serializer for blockchain statistics"""
    total_blocks = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    total_votes = serializers.IntegerField()
    last_block_time = serializers.DateTimeField()
    average_block_time = serializers.FloatField()
    chain_validity = serializers.BooleanField()
    current_difficulty = serializers.IntegerField()
    pending_transactions = serializers.IntegerField()


class BlockValidationSerializer(serializers.Serializer):
    """Serializer for block validation results"""
    block_index = serializers.IntegerField()
    is_valid = serializers.BooleanField()
    validation_errors = serializers.ListField(child=serializers.CharField())
    hash_verification = serializers.BooleanField()
    previous_hash_verification = serializers.BooleanField()
    proof_of_work_verification = serializers.BooleanField()
    timestamp_verification = serializers.BooleanField()


class ChainValidationSerializer(serializers.Serializer):
    """Serializer for blockchain validation results"""
    is_valid = serializers.BooleanField()
    total_blocks_checked = serializers.IntegerField()
    invalid_blocks = serializers.ListField(child=BlockValidationSerializer())
    validation_timestamp = serializers.DateTimeField()
    validation_duration = serializers.FloatField()


class MiningStatsSerializer(serializers.Serializer):
    """Serializer for mining statistics"""
    blocks_mined = serializers.IntegerField()
    total_mining_time = serializers.FloatField()
    average_mining_time = serializers.FloatField()
    current_difficulty = serializers.IntegerField()
    hash_rate = serializers.FloatField()
    last_mined_block = BlockSerializer()


class ProofVerificationSerializer(serializers.Serializer):
    """Serializer for vote proof verification"""
    vote_hash = serializers.CharField()
    block_hash = serializers.CharField()
    transaction_hash = serializers.CharField()
    is_valid = serializers.BooleanField()
    verification_details = serializers.DictField()
    timestamp = serializers.DateTimeField()
