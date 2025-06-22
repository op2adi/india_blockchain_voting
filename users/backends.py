from django.contrib.auth.backends import ModelBackend
from .models import Voter

class VoterAuthBackend(ModelBackend):
    """
    Custom authentication backend for Voter model.
    This allows login with voter_id instead of username.
    """
    
    def authenticate(self, request, voter_id=None, password=None, **kwargs):
        try:
            user = Voter.objects.get(voter_id=voter_id)
            if user.check_password(password):
                return user
        except Voter.DoesNotExist:
            # No user was found
            return None
        
    def get_user(self, user_id):
        try:
            return Voter.objects.get(pk=user_id)
        except Voter.DoesNotExist:
            return None
