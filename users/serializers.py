from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import Voter, AdminUser, VoterVerification, State, Constituency
import re


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name', 'code']


class ConstituencySerializer(serializers.ModelSerializer):
    state = StateSerializer(read_only=True)
    
    class Meta:
        model = Constituency
        fields = ['id', 'name', 'code', 'constituency_type', 'state', 
                 'total_voters', 'reserved_category']


class VoterRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    voter_card_number = serializers.CharField(write_only=True)
    aadhaar_number = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Voter
        fields = ['voter_id', 'email', 'first_name', 'last_name', 'password', 
                 'confirm_password', 'date_of_birth', 'gender', 'constituency',
                 'address_line1', 'address_line2', 'city', 'state', 'pincode',
                 'mobile_number', 'voter_card_number', 'aadhaar_number']
    
    def validate_voter_id(self, value):
        """Validate voter ID format"""
        pattern = r'^[A-Z]{3}\d{7}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Voter ID must be in format: ABC1234567 (3 letters + 7 digits)"
            )
        return value
    
    def validate_mobile_number(self, value):
        """Validate mobile number format"""
        pattern = r'^\+91\d{10}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Mobile number must be in format: +91XXXXXXXXXX"
            )
        return value
    
    def validate_pincode(self, value):
        """Validate pincode format"""
        pattern = r'^\d{6}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("Pincode must be 6 digits")
        return value
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return attrs
    
    def create(self, validated_data):
        """Create new voter with encrypted sensitive data"""
        # Remove confirm_password and sensitive data from validated_data
        validated_data.pop('confirm_password')
        voter_card_number = validated_data.pop('voter_card_number')
        aadhaar_number = validated_data.pop('aadhaar_number', None)
        
        # Create voter instance
        voter = Voter.objects.create_user(**validated_data)
        
        # Set encrypted sensitive data
        voter.set_voter_card_number(voter_card_number)
        if aadhaar_number:
            voter.set_aadhaar_number(aadhaar_number)
        
        voter.save()
        return voter


class VoterProfileSerializer(serializers.ModelSerializer):
    constituency = ConstituencySerializer(read_only=True)
    state = StateSerializer(read_only=True)
    
    class Meta:
        model = Voter
        fields = ['voter_id', 'email', 'first_name', 'last_name', 'date_of_birth',
                 'gender', 'constituency', 'address_line1', 'address_line2',
                 'city', 'state', 'pincode', 'mobile_number', 'is_verified',
                 'verification_date', 'has_voted', 'vote_count', 'last_voted_at',
                 'two_factor_enabled']
        read_only_fields = ['voter_id', 'is_verified', 'verification_date',
                           'has_voted', 'vote_count', 'last_voted_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer for voter login"""
    username_field = 'voter_id'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['voter_id'] = serializers.CharField()
        self.fields['password'] = serializers.CharField()
        del self.fields['username']
    
    def validate(self, attrs):
        voter_id = attrs.get('voter_id')
        password = attrs.get('password')
        
        # Check if voter exists and is active
        try:
            voter = Voter.objects.get(voter_id=voter_id)
        except Voter.DoesNotExist:
            raise serializers.ValidationError('Invalid voter ID or password')
        
        # Check if voter is locked
        if voter.is_locked and voter.locked_until and voter.locked_until > timezone.now():
            raise serializers.ValidationError(
                f'Account is locked until {voter.locked_until}'
            )
        
        # Authenticate voter
        user = authenticate(request=self.context.get('request'),
                          voter_id=voter_id, password=password)
        
        if user is None:
            # Increment failed login attempts
            voter.login_attempts += 1
            if voter.login_attempts >= 5:
                voter.is_locked = True
                voter.locked_until = timezone.now() + timezone.timedelta(minutes=30)
            voter.save()
            raise serializers.ValidationError('Invalid voter ID or password')
        
        # Reset failed attempts on successful login
        voter.login_attempts = 0
        voter.is_locked = False
        voter.locked_until = None
        voter.save()
        
        # Generate token
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': VoterProfileSerializer(user).data
        }
        
        return data


class FaceVerificationSerializer(serializers.Serializer):
    """Serializer for face recognition verification"""
    face_image = serializers.ImageField()
    voter_id = serializers.CharField()
    
    def validate_face_image(self, value):
        """Validate uploaded face image"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size should not exceed 5MB")
        
        # Check file format
        allowed_formats = ['jpeg', 'jpg', 'png']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_formats:
            raise serializers.ValidationError(
                "Only JPEG, JPG, and PNG formats are allowed"
            )
        
        return value


class TwoFactorAuthSerializer(serializers.Serializer):
    """Serializer for two-factor authentication"""
    verification_code = serializers.CharField(max_length=6)
    
    def validate_verification_code(self, value):
        """Validate 2FA code format"""
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("Verification code must be 6 digits")
        return value


class VoterVerificationSerializer(serializers.ModelSerializer):
    verified_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = VoterVerification
        fields = ['id', 'verification_type', 'status', 'verification_score',
                 'verified_by', 'verification_timestamp', 'expires_at', 'remarks']
        read_only_fields = ['verification_timestamp']


class AdminUserSerializer(serializers.ModelSerializer):
    user = VoterProfileSerializer(read_only=True)
    assigned_constituencies = ConstituencySerializer(many=True, read_only=True)
    
    class Meta:
        model = AdminUser
        fields = ['id', 'user', 'role', 'can_create_elections', 'can_manage_voters',
                 'can_view_results', 'can_audit_blockchain', 'can_manage_constituencies',
                 'assigned_constituencies', 'created_at']


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_new_password = serializers.CharField()
    
    def validate(self, attrs):
        """Validate passwords"""
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError("New passwords do not match")
        return attrs
    
    def validate_current_password(self, value):
        """Validate current password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value


class VoterLocationSerializer(serializers.Serializer):
    """Serializer for voter location verification"""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    accuracy = serializers.FloatField(required=False)
    timestamp = serializers.DateTimeField(required=False)
    
    def validate_latitude(self, value):
        """Validate latitude range"""
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude range"""
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value
