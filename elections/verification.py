from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from .models import VoteReceipt, VoteRecord
from blockchain.models import Block, VoteTransaction

logger = logging.getLogger(__name__)

class VerifyVoteView(APIView):
    """API endpoint for publicly verifying a vote without revealing voter identity"""
    
    def get(self, request, token, hash_prefix=None):
        try:
            # Find the receipt by verification token
            receipt = get_object_or_404(VoteReceipt, verification_token=token)
            
            # Optional check against hash prefix if provided
            if hash_prefix and not receipt.verification_hash.startswith(hash_prefix):
                return Response({
                    "verified": False,
                    "error": "Hash prefix does not match"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get vote record
            vote_record = receipt.vote_record
            
            # Get block and transaction details
            block = vote_record.block
            transaction_hash = vote_record.transaction_hash
            
            # Check if blockchain verification has already been done
            if not receipt.merkle_proof or not receipt.blockchain_position:
                # Generate cryptographic proof if not already done
                proof_generated = receipt.generate_cryptographic_proof()
                if not proof_generated:
                    # Still return basic information even if proof generation fails
                    return Response({
                        "verified": True,
                        "cryptographically_verified": False,
                        "receipt_id": str(receipt.receipt_id),
                        "block_index": block.index,
                        "timestamp": block.timestamp.isoformat(),
                        "election": vote_record.election.name,
                        "constituency": vote_record.constituency.name if vote_record.constituency else "Unknown",
                        "error": "Could not generate cryptographic proof"
                    })
            
            # Verify the cryptographic proof
            is_valid, details = receipt.verify_cryptographic_proof()
            
            # Get basic details about the vote (without revealing the actual vote content)
            response_data = {
                "verified": True,
                "cryptographically_verified": is_valid,
                "verification_details": details,
                "receipt_id": str(receipt.receipt_id),
                "block_index": block.index,
                "block_hash": block.hash,
                "timestamp": block.timestamp.isoformat(),
                "election": vote_record.election.name,
                "constituency": vote_record.constituency.name if vote_record.constituency else "Unknown",
                "blockchain_position": receipt.blockchain_position,
                "merkle_proof_available": bool(receipt.merkle_proof)
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error verifying vote: {str(e)}")
            return Response({
                "verified": False,
                "error": "Error processing verification request"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def vote_verification_page(request, token, hash_prefix=None):
    """User-friendly verification page for voters to check their vote"""
    try:
        receipt = get_object_or_404(VoteReceipt, verification_token=token)
        
        # Optional check against hash prefix
        if hash_prefix and not receipt.verification_hash.startswith(hash_prefix):
            return render(request, 'elections/vote_verification_failed.html', {
                'error': "Verification code mismatch"
            })
            
        # Get vote record and block details
        vote_record = receipt.vote_record
        block = vote_record.block
        
        # Generate cryptographic proof if needed
        if not receipt.merkle_proof or not receipt.blockchain_position:
            receipt.generate_cryptographic_proof()
            
        # Verify cryptographic proof
        is_valid, details = receipt.verify_cryptographic_proof()
        
        context = {
            'receipt': receipt,
            'vote_record': vote_record,
            'block': block,
            'election': vote_record.election,
            'cryptographically_verified': is_valid,
            'verification_details': details,
            'block_data': block.blockchain_position if hasattr(block, 'blockchain_position') else None
        }
        
        return render(request, 'elections/vote_verification.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying vote verification: {str(e)}")
        return render(request, 'elections/vote_verification_failed.html', {
            'error': "Could not verify vote"
        })
