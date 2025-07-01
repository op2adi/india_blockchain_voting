"""
Face recognition utilities for the blockchain voting system.
This module provides face recognition functionality with fallback support.
"""
import logging
import numpy as np
import base64
import tempfile
import os
from io import BytesIO
from PIL import Image
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import face recognition libraries
try:
    import face_recognition
    import cv2
    FACE_RECOGNITION_AVAILABLE = True
    logger.info("Face recognition libraries loaded successfully")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("Face recognition libraries not available. Face verification will be disabled.")


def is_face_recognition_available():
    """Check if face recognition is available"""
    return FACE_RECOGNITION_AVAILABLE


def extract_face_encoding(image_path_or_array):
    """Extract face encoding from image"""
    if not FACE_RECOGNITION_AVAILABLE:
        logger.warning("Face recognition not available")
        return None
    
    try:
        # Load image
        if isinstance(image_path_or_array, str):
            image = face_recognition.load_image_file(image_path_or_array)
        else:
            image = image_path_or_array
        
        # Find face encodings
        face_encodings = face_recognition.face_encodings(image)
        
        if len(face_encodings) == 0:
            return None
        
        # Return the first face encoding found
        return face_encodings[0]
    
    except Exception as e:
        logger.error(f"Error extracting face encoding: {e}")
        return None


def compare_faces(known_encoding, unknown_encoding, tolerance=0.6):
    """Compare two face encodings"""
    if not FACE_RECOGNITION_AVAILABLE:
        logger.warning("Face recognition not available")
        return False, 0.0
    
    if known_encoding is None or unknown_encoding is None:
        return False, 0.0
    
    try:
        # Convert to numpy arrays if needed
        if not isinstance(known_encoding, np.ndarray):
            known_encoding = np.array(known_encoding)
        if not isinstance(unknown_encoding, np.ndarray):
            unknown_encoding = np.array(unknown_encoding)
        
        # Calculate face distance
        face_distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
        
        # Determine if faces match
        is_match = face_distance <= tolerance
        confidence = 1 - face_distance  # Convert distance to confidence score
        
        return is_match, confidence
    
    except Exception as e:
        logger.error(f"Error comparing faces: {e}")
        return False, 0.0


def validate_face_image_quality(image_path_or_array):
    """Validate if image has good quality for face recognition"""
    if not FACE_RECOGNITION_AVAILABLE:
        return True, "Face recognition not available, skipping quality check"
    
    try:
        # Load image
        if isinstance(image_path_or_array, str):
            image = cv2.imread(image_path_or_array)
        else:
            image = image_path_or_array
        
        if image is None:
            return False, "Could not load image"
        
        # Check image dimensions
        height, width = image.shape[:2]
        if width < 200 or height < 200:
            return False, "Image resolution too low (minimum 200x200 pixels)"
        
        # Check if face is detectable
        face_locations = face_recognition.face_locations(image)
        if len(face_locations) == 0:
            return False, "No face detected in image"
        
        if len(face_locations) > 1:
            return False, "Multiple faces detected, please use image with single face"
        
        # Check face size relative to image
        top, right, bottom, left = face_locations[0]
        face_width = right - left
        face_height = bottom - top
        
        if face_width < 100 or face_height < 100:
            return False, "Face too small in image"
        
        # Check if face takes up reasonable portion of image
        face_area = face_width * face_height
        image_area = width * height
        face_ratio = face_area / image_area
        
        if face_ratio < 0.1:
            return False, "Face too small relative to image size"
        
        if face_ratio > 0.8:
            return False, "Face too large, please move camera back"
        
        return True, "Face image quality is good"
    
    except Exception as e:
        logger.error(f"Error validating face image quality: {e}")
        return False, f"Error validating image: {str(e)}"


def process_face_image_for_encoding(image_file):
    """Process uploaded image file for face encoding"""
    if not FACE_RECOGNITION_AVAILABLE:
        return None, "Face recognition not available"
    
    try:
        from PIL import Image
        import io
        
        # Read image file
        image_data = image_file.read()
        image_file.seek(0)  # Reset file pointer
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        # Validate image quality
        is_valid, message = validate_face_image_quality(image_array)
        if not is_valid:
            return None, message
        
        # Extract face encoding
        encoding = extract_face_encoding(image_array)
        if encoding is None:
            return None, "Could not extract face features from image"
        
        return encoding.tolist(), "Face encoding extracted successfully"
    
    except Exception as e:
        logger.error(f"Error processing face image: {e}")
        return None, f"Error processing image: {str(e)}"


def create_mock_face_encoding():
    """Create a mock face encoding for testing when face recognition is not available"""
    import random
    # Create a random 128-dimensional vector (same as face_recognition library)
    return [random.random() for _ in range(128)]


def verify_voter_face(voter, uploaded_image_file):
    """Verify voter's face against stored encoding"""
    if not FACE_RECOGNITION_AVAILABLE:
        logger.warning("Face recognition not available, returning mock verification")
        return True, 0.95, "Face recognition disabled"
    
    try:
        # Get stored face encoding
        stored_encoding = voter.get_face_encoding()
        if not stored_encoding:
            return False, 0.0, "No face encoding stored for voter"
        
        # Process uploaded image
        uploaded_encoding, message = process_face_image_for_encoding(uploaded_image_file)
        if uploaded_encoding is None:
            return False, 0.0, message
        
        # Compare faces
        is_match, confidence = compare_faces(stored_encoding, uploaded_encoding)
        
        status_message = "Face verification successful" if is_match else "Face verification failed"
        return is_match, confidence, status_message
    
    except Exception as e:
        logger.error(f"Error verifying voter face: {e}")
        return False, 0.0, f"Face verification error: {str(e)}"
