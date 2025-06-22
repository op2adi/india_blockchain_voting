from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
# from rest_framework import generics, status, permissions
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
from django.views import View

# Mock APIView for basic functionality
class APIView(View):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)go.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
import json
import secrets

# Optional imports
try:
    import qrcode
    QR_CODE_AVAILABLE = True
except ImportError:
    QR_CODE_AVAILABLE = False

# Optional imports for face recognition
try:
    import cv2
    import numpy as np
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

from .face_recognition import (
    is_face_recognition_available, verify_voter_face, 
    process_face_image_for_encoding
)
from io import BytesIO
from PIL import Image

from .models import Voter, AdminUser, VoterVerification, State, Constituency, VoterSession
from .serializers import (
    VoterRegistrationSerializer, VoterProfileSerializer, CustomTokenObtainPairSerializer,
    FaceVerificationSerializer, TwoFactorAuthSerializer, VoterVerificationSerializer,
    StateSerializer, ConstituencySerializer, PasswordChangeSerializer,
    VoterLocationSerializer
)
from .utils import send_sms, send_email, generate_2fa_code, verify_2fa_code

logger = logging.getLogger(__name__)


class VoterRegistrationView(generics.CreateAPIView):
    """API endpoint for voter registration"""
    queryset = Voter.objects.all()
    serializer_class = VoterRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Register a new voter",
        responses={
            201: VoterProfileSerializer(),
            400: "Bad Request - Validation errors"
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            voter = serializer.save()
            
            # Create verification record
            VoterVerification.objects.create(
                voter=voter,
                verification_type='MANUAL',
                status='PENDING',
                verification_data={'registration_ip': self.get_client_ip(request)},
                verification_ip=self.get_client_ip(request)
            )
            
            # Log registration
            logger.info(f"New voter registered: {voter.voter_id}")
            
            return Response(
                VoterProfileSerializer(voter).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view for voter login"""
    serializer_class = CustomTokenObtainPairSerializer
    
    @swagger_auto_schema(
        operation_description="Login voter and obtain JWT tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'voter_id': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: "Success - Returns access and refresh tokens",
            401: "Unauthorized - Invalid credentials"
        }
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Create session record
            voter = Voter.objects.get(voter_id=request.data.get('voter_id'))
            session_key = secrets.token_urlsafe(32)
            
            VoterSession.objects.create(
                voter=voter,
                session_key=session_key,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                device_fingerprint=self.generate_device_fingerprint(request),
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            
            # Update last login
            voter.last_login = timezone.now()
            voter.last_login_ip = self.get_client_ip(request)
            voter.save()
            
            # Add session key to response
            response.data['session_key'] = session_key
            
            logger.info(f"Voter login successful: {voter.voter_id}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def generate_device_fingerprint(self, request):
        """Generate device fingerprint"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        fingerprint_data = f"{user_agent}:{accept_language}"
        return hash(fingerprint_data) % (10 ** 8)


class VoterProfileView(generics.RetrieveUpdateAPIView):
    """API endpoint for voter profile management"""
    serializer_class = VoterProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @swagger_auto_schema(
        operation_description="Get voter profile",
        responses={200: VoterProfileSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update voter profile",
        responses={200: VoterProfileSerializer()}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class FaceVerificationView(APIView):
    """API endpoint for face recognition verification"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Verify voter using face recognition",
        request_body=FaceVerificationSerializer,
        responses={
            200: "Success - Face verified",
            400: "Bad Request - Face not recognized",
            404: "Not Found - Voter not found"
        }
    )
    def post(self, request):
        serializer = FaceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        voter_id = serializer.validated_data['voter_id']
        face_image = serializer.validated_data['face_image']
        
        try:
            voter = Voter.objects.get(voter_id=voter_id)
        except Voter.DoesNotExist:
            return Response(
                {'error': 'Voter not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Process face image
        face_verification_result = self.verify_face(face_image, voter)
        
        if face_verification_result['verified']:
            # Create verification record
            VoterVerification.objects.create(
                voter=voter,
                verification_type='FACE',
                status='VERIFIED',
                verification_data=face_verification_result,
                verification_score=face_verification_result['confidence'],
                verification_ip=self.get_client_ip(request)
            )
            
            # Update voter verification status
            voter.is_verified = True
            voter.verification_date = timezone.now()
            voter.save()
            
            logger.info(f"Face verification successful for voter: {voter_id}")
            
            return Response({
                'verified': True,
                'confidence': face_verification_result['confidence'],
                'message': 'Face verification successful'
            })
        else:
            # Create failed verification record
            VoterVerification.objects.create(
                voter=voter,
                verification_type='FACE',
                status='REJECTED',
                verification_data=face_verification_result,
                verification_score=face_verification_result['confidence'],
                verification_ip=self.get_client_ip(request),
                remarks='Face recognition failed'
            )
            
            logger.warning(f"Face verification failed for voter: {voter_id}")
            
            return Response({
                'verified': False,
                'confidence': face_verification_result['confidence'],
                'message': 'Face verification failed'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def verify_face(self, face_image, voter):
        """Verify face using face_recognition library"""
        try:
            # Convert uploaded image to numpy array
            image = Image.open(face_image)
            image_np = np.array(image)
            
            # Convert RGB to BGR for OpenCV
            if len(image_np.shape) == 3:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
            # Find face encodings in uploaded image
            face_locations = face_recognition.face_locations(image_np)
            if not face_locations:
                return {'verified': False, 'confidence': 0.0, 'error': 'No face found in image'}
            
            face_encodings = face_recognition.face_encodings(image_np, face_locations)
            if not face_encodings:
                return {'verified': False, 'confidence': 0.0, 'error': 'Could not encode face'}
            
            uploaded_encoding = face_encodings[0]
            
            # Get stored face encoding
            stored_encoding = voter.get_face_encoding()
            if not stored_encoding:
                return {'verified': False, 'confidence': 0.0, 'error': 'No stored face encoding'}
            
            # Compare faces
            face_distances = face_recognition.face_distance([stored_encoding], uploaded_encoding)
            confidence = 1 - face_distances[0]  # Convert distance to confidence
            
            # Use tolerance from settings
            from django.conf import settings
            tolerance = getattr(settings, 'FACE_RECOGNITION_TOLERANCE', 0.6)
            verified = face_distances[0] < tolerance
            
            return {
                'verified': verified,
                'confidence': float(confidence),
                'face_distance': float(face_distances[0]),
                'tolerance_used': tolerance
            }
            
        except Exception as e:
            logger.error(f"Face verification error: {str(e)}")
            return {'verified': False, 'confidence': 0.0, 'error': str(e)}
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TwoFactorAuthView(APIView):
    """API endpoint for two-factor authentication"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Send 2FA code to voter",
        responses={200: "Success - 2FA code sent"}
    )
    def post(self, request):
        voter = request.user
        
        # Generate 2FA code
        code = generate_2fa_code()
        
        # Store code in cache (expires in 5 minutes)
        cache_key = f"2fa_code_{voter.voter_id}"
        cache.set(cache_key, code, 300)
        
        # Send SMS
        try:
            send_sms(voter.mobile_number, f"Your voting verification code is: {code}")
            logger.info(f"2FA code sent to voter: {voter.voter_id}")
            
            return Response({
                'message': '2FA code sent successfully',
                'expires_in': 300
            })
        except Exception as e:
            logger.error(f"Failed to send 2FA code: {str(e)}")
            return Response(
                {'error': 'Failed to send 2FA code'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_description="Verify 2FA code",
        request_body=TwoFactorAuthSerializer,
        responses={
            200: "Success - 2FA verified",
            400: "Bad Request - Invalid code"
        }
    )
    def put(self, request):
        serializer = TwoFactorAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        voter = request.user
        verification_code = serializer.validated_data['verification_code']
        
        # Verify code
        cache_key = f"2fa_code_{voter.voter_id}"
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == verification_code:
            # Clear the code from cache
            cache.delete(cache_key)
            
            # Create verification record
            VoterVerification.objects.create(
                voter=voter,
                verification_type='OTP',
                status='VERIFIED',
                verification_data={'code_verified': True},
                verification_score=100.0,
                verification_ip=self.get_client_ip(request)
            )
            
            # Update voter 2FA status
            voter.two_factor_enabled = True
            voter.save()
            
            logger.info(f"2FA verification successful for voter: {voter.voter_id}")
            
            return Response({'message': '2FA verification successful'})
        else:
            logger.warning(f"2FA verification failed for voter: {voter.voter_id}")
            return Response(
                {'error': 'Invalid or expired verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordChangeView(APIView):
    """API endpoint for password change"""
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Change voter password",
        request_body=PasswordChangeSerializer,
        responses={
            200: "Success - Password changed",
            400: "Bad Request - Validation errors"
        }
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            voter = request.user
            new_password = serializer.validated_data['new_password']
            
            # Change password
            voter.set_password(new_password)
            voter.save()
            
            logger.info(f"Password changed for voter: {voter.voter_id}")
            
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VoterVerificationListView(generics.ListAPIView):
    """API endpoint to list voter verifications"""
    serializer_class = VoterVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return VoterVerification.objects.filter(voter=self.request.user)


class StateListView(generics.ListAPIView):
    """API endpoint to list all states"""
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [permissions.AllowAny]


class ConstituencyListView(generics.ListAPIView):
    """API endpoint to list constituencies"""
    serializer_class = ConstituencySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        state_id = self.request.query_params.get('state_id')
        queryset = Constituency.objects.all()
        
        if state_id:
            queryset = queryset.filter(state_id=state_id)
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_face_image(request):
    """Upload face image for verification"""
    if 'face_image' not in request.FILES:
        return Response(
            {'error': 'No face image provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    face_image = request.FILES['face_image']
    voter = request.user
    
    try:
        # Process and store face encoding
        image = Image.open(face_image)
        image_np = np.array(image)
        
        # Find face encoding
        face_locations = face_recognition.face_locations(image_np)
        if not face_locations:
            return Response(
                {'error': 'No face found in image'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        face_encodings = face_recognition.face_encodings(image_np, face_locations)
        if not face_encodings:
            return Response(
                {'error': 'Could not encode face'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store face encoding
        voter.set_face_encoding(face_encodings[0])
        voter.save()
        
        logger.info(f"Face image uploaded for voter: {voter.voter_id}")
        
        return Response({'message': 'Face image uploaded successfully'})
    
    except Exception as e:
        logger.error(f"Face image upload error: {str(e)}")
        return Response(
            {'error': 'Failed to process face image'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_location(request):
    """Verify voter location"""
    serializer = VoterLocationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    voter = request.user
    location_data = serializer.validated_data
    
    # Verify if voter is in correct constituency (mock implementation)
    # In production, implement proper geofencing
    is_valid_location = True  # Always true for now
    
    # Create verification record
    VoterVerification.objects.create(
        voter=voter,
        verification_type='LOCATION',
        status='VERIFIED' if is_valid_location else 'REJECTED',
        verification_data=location_data,
        verification_score=100.0 if is_valid_location else 0.0,
        verification_ip=request.META.get('REMOTE_ADDR')
    )
    
    return Response({
        'verified': is_valid_location,
        'message': 'Location verified' if is_valid_location else 'Invalid location'
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def voter_dashboard(request):
    """Get voter dashboard data"""
    voter = request.user
    
    # Get active elections
    from elections.models import Election
    from elections.serializers import ElectionSerializer
    
    active_elections = Election.objects.filter(
        status='VOTING_OPEN',
        constituencies__in=[voter.constituency]
    ).distinct()
    
    # Get voting history
    from elections.models import VoteRecord
    from elections.serializers import VoteRecordSerializer
    
    voting_history = VoteRecord.objects.filter(
        voter_hash=hash(voter.voter_id)  # Simplified for demo
    )[:10]
    
    # Get verification status
    verifications = VoterVerification.objects.filter(voter=voter)
    verification_status = {
        'face_verified': verifications.filter(
            verification_type='FACE', status='VERIFIED'
        ).exists(),
        'phone_verified': verifications.filter(
            verification_type='OTP', status='VERIFIED'
        ).exists(),
        'location_verified': verifications.filter(
            verification_type='LOCATION', status='VERIFIED'
        ).exists(),
        'overall_verified': voter.is_verified
    }
    
    dashboard_data = {
        'voter_info': VoterProfileSerializer(voter).data,
        'active_elections': ElectionSerializer(active_elections, many=True).data,
        'voting_history': VoteRecordSerializer(voting_history, many=True).data,
        'verification_status': verification_status,
        'notifications': []  # Add notifications logic
    }
    
    return Response(dashboard_data)

# Frontend Views
def register_view(request):
    """Voter registration page"""
    return render(request, 'users/register.html')

def login_view(request):
    """Login page"""
    return render(request, 'users/login.html')

def logout_view(request):
    """Logout view"""
    return render(request, 'users/logout.html')

def profile_view(request):
    """User profile page"""
    return render(request, 'users/profile.html')

# API Views - Basic implementations
class CustomTokenObtainPairView(APIView):
    """Basic token obtain view"""
    def post(self, request):
        return JsonResponse({'message': 'Login endpoint not fully implemented yet'})

class VerifyVoterView(APIView):
    """Basic voter verification view"""
    def post(self, request):
        return JsonResponse({'message': 'Voter verification endpoint not fully implemented yet'})

class TwoFactorAuthView(APIView):
    """Basic 2FA view"""
    def post(self, request):
        return JsonResponse({'message': '2FA endpoint not fully implemented yet'})

class FaceVerificationView(APIView):
    """Basic face verification view"""
    def post(self, request):
        return JsonResponse({'message': 'Face verification endpoint not fully implemented yet'})

class AdminVoterListView(APIView):
    """Basic admin voter list view"""
    def get(self, request):
        return JsonResponse({'message': 'Admin voter list endpoint not fully implemented yet'})
