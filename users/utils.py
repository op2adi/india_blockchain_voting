import secrets
import random
import string
import logging
from django.core.mail import send_mail
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


def generate_2fa_code():
    """Generate a 6-digit 2FA code"""
    return ''.join(random.choices(string.digits, k=6))


def verify_2fa_code(stored_code, provided_code):
    """Verify 2FA code"""
    return stored_code == provided_code


def send_sms(phone_number, message):
    """Send SMS using SMS service provider"""
    # Mock SMS implementation
    # In production, integrate with SMS service like Twilio, AWS SNS, or local SMS gateway
    
    logger.info(f"SMS sent to {phone_number}: {message}")
    
    # Mock successful response
    return {
        'success': True,
        'message_id': secrets.token_hex(8),
        'status': 'sent'
    }


def send_email(to_email, subject, message, html_message=None):
    """Send email notification"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def generate_secure_token(length=32):
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def validate_voter_id_format(voter_id):
    """Validate voter ID format"""
    import re
    pattern = r'^[A-Z]{3}\d{7}$'
    return bool(re.match(pattern, voter_id))


def validate_mobile_number_format(mobile_number):
    """Validate mobile number format"""
    import re
    pattern = r'^\+91\d{10}$'
    return bool(re.match(pattern, mobile_number))


def hash_voter_data(voter_id, constituency_code, salt=None):
    """Create a secure hash of voter data"""
    import hashlib
    
    if salt is None:
        salt = secrets.token_hex(16)
    
    combined = f"{voter_id}:{constituency_code}:{salt}"
    return hashlib.sha256(combined.encode()).hexdigest(), salt


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_device_fingerprint(request):
    """Generate device fingerprint from request headers"""
    import hashlib
    
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
    
    fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()


def send_verification_email(voter, verification_type, verification_code):
    """Send verification email to voter"""
    subject = f"Blockchain Voting - {verification_type} Verification"
    
    message = f"""
    Dear {voter.get_full_name()},
    
    Your verification code for {verification_type} is: {verification_code}
    
    This code will expire in 5 minutes.
    
    If you did not request this verification, please ignore this email.
    
    Best regards,
    Blockchain Voting System
    """
    
    html_message = f"""
    <html>
    <body>
        <h2>Blockchain Voting System</h2>
        <p>Dear {voter.get_full_name()},</p>
        <p>Your verification code for <strong>{verification_type}</strong> is:</p>
        <h1 style="color: #007bff; font-size: 2em; letter-spacing: 5px;">{verification_code}</h1>
        <p>This code will expire in 5 minutes.</p>
        <p>If you did not request this verification, please ignore this email.</p>
        <p>Best regards,<br>Blockchain Voting System</p>
    </body>
    </html>
    """
    
    return send_email(voter.email, subject, message, html_message)


def generate_qr_code(data, size=(300, 300)):
    """Generate QR code for data"""
    import qrcode
    from io import BytesIO
    from PIL import Image
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize(size)
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer


def create_audit_log(action, actor_type, actor_id, details, ip_address, success=True, error_message=""):
    """Create audit log entry"""
    from elections.models import ElectionAuditLog
    
    try:
        ElectionAuditLog.objects.create(
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            details=details,
            success=success,
            error_message=error_message,
            ip_address=ip_address
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")


def encrypt_sensitive_data(data, key):
    """Encrypt sensitive data"""
    from cryptography.fernet import Fernet
    import json
    
    f = Fernet(key)
    return f.encrypt(json.dumps(data).encode()).decode()


def decrypt_sensitive_data(encrypted_data, key):
    """Decrypt sensitive data"""
    from cryptography.fernet import Fernet
    import json
    
    f = Fernet(key)
    decrypted_bytes = f.decrypt(encrypted_data.encode())
    return json.loads(decrypted_bytes.decode())


def validate_face_image(image_file):
    """Validate uploaded face image"""
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError:
        logger.warning("OpenCV not available, basic image validation only")
        # Basic validation without OpenCV
        if image_file.size > 5 * 1024 * 1024:
            return False, "Image size should not exceed 5MB"
        
        allowed_formats = ['jpeg', 'jpg', 'png']
        file_extension = image_file.name.split('.')[-1].lower()
        if file_extension not in allowed_formats:
            return False, "Only JPEG, JPG, and PNG formats are allowed"
        
        return True, "Image format valid"
    
    try:
        # Check file size (max 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return False, "Image size should not exceed 5MB"
        
        # Check file format
        allowed_formats = ['jpeg', 'jpg', 'png']
        file_extension = image_file.name.split('.')[-1].lower()
        if file_extension not in allowed_formats:
            return False, "Only JPEG, JPG, and PNG formats are allowed"
        
        # Try to open and process image
        image = Image.open(image_file)
        image_np = np.array(image)
        
        # Check if image can be processed by OpenCV
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            # Valid RGB image
            return True, "Valid image"
        elif len(image_np.shape) == 2:
            # Grayscale image
            return True, "Valid grayscale image"
        else:
            return False, "Invalid image format"
            
    except Exception as e:
        return False, f"Error processing image: {str(e)}"


def get_geolocation_from_ip(ip_address):
    """Get geolocation from IP address"""
    # Mock implementation
    # In production, integrate with geolocation service like MaxMind or ipapi
    
    return {
        'country': 'India',
        'state': 'Unknown',
        'city': 'Unknown',
        'latitude': 20.5937,
        'longitude': 78.9629,
        'accuracy': 'country'
    }


def verify_constituency_location(voter_constituency, voter_location):
    """Verify if voter is in correct constituency"""
    # Mock implementation
    # In production, implement proper geofencing using constituency boundaries
    
    return True  # Always allow for now


def calculate_age(birth_date):
    """Calculate age from birth date"""
    from datetime import date
    
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def is_eligible_to_vote(voter):
    """Check if voter is eligible to vote"""
    age = calculate_age(voter.date_of_birth)
    return age >= 18 and voter.is_verified and voter.is_active


def generate_receipt_data(vote_record):
    """Generate receipt data for vote"""
    import json
    from datetime import datetime
    
    receipt_data = {
        'vote_id': str(vote_record.vote_id),
        'election_name': vote_record.election.name,
        'constituency': vote_record.constituency.name,
        'vote_type': vote_record.vote_type,
        'timestamp': vote_record.voting_timestamp.isoformat(),
        'block_hash': vote_record.block.hash,
        'transaction_hash': vote_record.transaction_hash,
        'verification_method': vote_record.verification_method,
        'generated_at': datetime.now().isoformat()
    }
    
    return receipt_data
