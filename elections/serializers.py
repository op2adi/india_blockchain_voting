from rest_framework import serializers
from .models import (Party, Election, Candidate, VoteRecord, VoteReceipt, 
                     ElectionResult, CandidateVoteCount, ElectionAuditLog,
                     ElectionConstituency)
from users.serializers import ConstituencySerializer, StateSerializer
from blockchain.serializers import BlockSerializer


class PartySerializer(serializers.ModelSerializer):
    recognized_states = StateSerializer(many=True, read_only=True)
    
    class Meta:
        model = Party
        fields = ['id', 'name', 'abbreviation', 'symbol', 'symbol_image',
                 'founded_date', 'headquarters', 'website', 'recognition_status',
                 'recognized_states', 'party_color', 'is_active', 'created_at']


class PartyStatsSerializer(serializers.ModelSerializer):
    """Party serializer with vote statistics"""
    total_votes = serializers.IntegerField(read_only=True)
    total_constituencies = serializers.IntegerField(read_only=True)
    winning_constituencies = serializers.IntegerField(read_only=True)
    vote_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Party
        fields = ['id', 'name', 'abbreviation', 'symbol', 'party_color',
                 'total_votes', 'total_constituencies', 'winning_constituencies',
                 'vote_percentage']


class ElectionConstituencySerializer(serializers.ModelSerializer):
    constituency = ConstituencySerializer(read_only=True)
    
    class Meta:
        model = ElectionConstituency
        fields = ['id', 'constituency', 'polling_start_time', 'polling_end_time',
                 'total_votes_cast', 'total_valid_votes', 'total_invalid_votes',
                 'voter_turnout_percentage', 'is_active']


class ElectionSerializer(serializers.ModelSerializer):
    state = StateSerializer(read_only=True)
    constituencies = ElectionConstituencySerializer(
        source='electionconstituency_set', many=True, read_only=True
    )
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Election
        fields = ['id', 'name', 'election_type', 'election_id', 'state',
                 'constituencies', 'announcement_date', 'nomination_start_date',
                 'nomination_end_date', 'voting_start_date', 'voting_end_date',
                 'result_date', 'status', 'allow_nota', 'require_photo_id',
                 'enable_face_verification', 'description', 'created_by',
                 'created_at']


class ElectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating elections"""
    constituency_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    
    class Meta:
        model = Election
        fields = ['name', 'election_type', 'election_id', 'state',
                 'announcement_date', 'nomination_start_date', 'nomination_end_date',
                 'voting_start_date', 'voting_end_date', 'result_date',
                 'allow_nota', 'require_photo_id', 'enable_face_verification',
                 'description', 'constituency_ids']
    
    def validate_constituency_ids(self, value):
        """Validate constituency IDs exist"""
        from users.models import Constituency
        valid_ids = Constituency.objects.filter(id__in=value).values_list('id', flat=True)
        if len(valid_ids) != len(value):
            raise serializers.ValidationError("Some constituency IDs are invalid")
        return value
    
    def validate(self, attrs):
        """Validate election dates"""
        dates = [
            ('announcement_date', attrs['announcement_date']),
            ('nomination_start_date', attrs['nomination_start_date']),
            ('nomination_end_date', attrs['nomination_end_date']),
            ('voting_start_date', attrs['voting_start_date']),
            ('voting_end_date', attrs['voting_end_date']),
            ('result_date', attrs['result_date'])
        ]
        
        # Check chronological order
        for i in range(len(dates) - 1):
            if dates[i][1] >= dates[i + 1][1]:
                raise serializers.ValidationError(
                    f"{dates[i][0]} must be before {dates[i + 1][0]}"
                )
        
        return attrs


class CandidateSerializer(serializers.ModelSerializer):
    party = PartySerializer(read_only=True)
    constituency = ConstituencySerializer(read_only=True)
    election = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'father_name', 'mother_name', 'date_of_birth',
                 'gender', 'party', 'is_independent', 'election', 'constituency',
                 'candidate_number', 'nomination_id', 'nomination_date',
                 'nomination_status', 'education', 'profession', 'assets_value',
                 'criminal_cases', 'address', 'phone_number', 'email', 'photo',
                 'symbol', 'symbol_image', 'votes_received', 'vote_percentage',
                 'rank', 'is_winner']


class CandidateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating candidates"""
    party_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Candidate
        fields = ['name', 'father_name', 'mother_name', 'date_of_birth', 'gender',
                 'party_id', 'is_independent', 'candidate_number', 'nomination_id',
                 'nomination_date', 'education', 'profession', 'assets_value',
                 'criminal_cases', 'address', 'phone_number', 'email', 'photo',
                 'symbol', 'symbol_image']
    
    def validate(self, attrs):
        """Validate candidate data"""
        if attrs.get('is_independent') and attrs.get('party_id'):
            raise serializers.ValidationError(
                "Independent candidate cannot have a party"
            )
        
        if not attrs.get('is_independent') and not attrs.get('party_id'):
            raise serializers.ValidationError(
                "Non-independent candidate must have a party"
            )
        
        return attrs


class VoteSerializer(serializers.Serializer):
    """Serializer for casting votes"""
    election_id = serializers.IntegerField()
    constituency_id = serializers.IntegerField()
    candidate_id = serializers.IntegerField(required=False, allow_null=True)
    vote_type = serializers.ChoiceField(choices=VoteRecord.VOTE_TYPES)
    verification_method = serializers.CharField(max_length=50)
    location_data = serializers.JSONField(required=False)
    
    def validate(self, attrs):
        """Validate vote data"""
        vote_type = attrs['vote_type']
        candidate_id = attrs.get('candidate_id')
        
        if vote_type == 'CANDIDATE' and not candidate_id:
            raise serializers.ValidationError(
                "Candidate ID is required for candidate votes"
            )
        
        if vote_type != 'CANDIDATE' and candidate_id:
            raise serializers.ValidationError(
                "Candidate ID should not be provided for non-candidate votes"
            )
        
        # Validate election is open for voting
        try:
            from .models import Election
            election = Election.objects.get(id=attrs['election_id'])
            if not election.is_voting_open():
                raise serializers.ValidationError("Voting is not currently open")
        except Election.DoesNotExist:
            raise serializers.ValidationError("Invalid election ID")
        
        return attrs


class VoteRecordSerializer(serializers.ModelSerializer):
    election = serializers.StringRelatedField(read_only=True)
    constituency = ConstituencySerializer(read_only=True)
    candidate = CandidateSerializer(read_only=True)
    block = BlockSerializer(read_only=True)
    
    class Meta:
        model = VoteRecord
        fields = ['vote_id', 'election', 'constituency', 'candidate', 'vote_type',
                 'block', 'transaction_hash', 'voter_hash', 'voting_timestamp',
                 'verification_method', 'verification_score', 'polling_station_id']


class VoteReceiptSerializer(serializers.ModelSerializer):
    vote_record = VoteRecordSerializer(read_only=True)
    
    class Meta:
        model = VoteReceipt
        fields = ['receipt_id', 'vote_record', 'receipt_data', 'qr_code',
                 'pdf_file', 'digital_signature', 'verification_hash',
                 'is_downloaded', 'download_count', 'created_at']


class ElectionResultSerializer(serializers.ModelSerializer):
    election = ElectionSerializer(read_only=True)
    constituency = ConstituencySerializer(read_only=True)
    winning_candidate = CandidateSerializer(read_only=True)
    winning_party = PartySerializer(read_only=True)
    candidate_votes = serializers.SerializerMethodField()
    
    class Meta:
        model = ElectionResult
        fields = ['id', 'election', 'constituency', 'total_voters', 'total_votes_cast',
                 'total_valid_votes', 'total_invalid_votes', 'nota_votes',
                 'voter_turnout_percentage', 'winning_candidate', 'winning_party',
                 'winning_margin', 'victory_margin_percentage', 'status',
                 'result_hash', 'blockchain_verified', 'counting_start_time',
                 'result_declared_time', 'candidate_votes']
    
    def get_candidate_votes(self, obj):
        """Get candidate vote counts for this result"""
        candidate_votes = CandidateVoteCount.objects.filter(
            election_result=obj
        ).order_by('rank')
        return CandidateVoteCountSerializer(candidate_votes, many=True).data


class CandidateVoteCountSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer(read_only=True)
    
    class Meta:
        model = CandidateVoteCount
        fields = ['candidate', 'votes_count', 'vote_percentage', 'rank', 'round_number']


class LeaderboardSerializer(serializers.Serializer):
    """Serializer for election leaderboard"""
    party_id = serializers.IntegerField()
    party_name = serializers.CharField()
    party_abbreviation = serializers.CharField()
    party_symbol = serializers.CharField()
    party_color = serializers.CharField()
    total_votes = serializers.IntegerField()
    total_constituencies = serializers.IntegerField()
    winning_constituencies = serializers.IntegerField()
    vote_percentage = serializers.FloatField()
    rank = serializers.IntegerField()


class ElectionStatsSerializer(serializers.Serializer):
    """Serializer for election statistics"""
    total_voters = serializers.IntegerField()
    total_votes_cast = serializers.IntegerField()
    total_valid_votes = serializers.IntegerField()
    total_invalid_votes = serializers.IntegerField()
    nota_votes = serializers.IntegerField()
    voter_turnout_percentage = serializers.FloatField()
    constituencies_completed = serializers.IntegerField()
    total_constituencies = serializers.IntegerField()
    counting_status = serializers.CharField()


class ElectionAuditLogSerializer(serializers.ModelSerializer):
    election = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = ElectionAuditLog
        fields = ['id', 'election', 'action', 'actor_type', 'actor_id',
                 'details', 'success', 'error_message', 'ip_address',
                 'user_agent', 'timestamp']


class VoterDashboardSerializer(serializers.Serializer):
    """Serializer for voter dashboard data"""
    voter_info = serializers.DictField()
    active_elections = ElectionSerializer(many=True)
    voting_history = VoteRecordSerializer(many=True)
    verification_status = serializers.DictField()
    notifications = serializers.ListField()


class AdminDashboardSerializer(serializers.Serializer):
    """Serializer for admin dashboard data"""
    election_summary = serializers.DictField()
    live_voting_stats = serializers.DictField()
    recent_activities = ElectionAuditLogSerializer(many=True)
    system_health = serializers.DictField()
    blockchain_status = serializers.DictField()
