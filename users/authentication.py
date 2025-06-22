from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import Voter

class VoterAuthBackend(ModelBackend):
    """
    Authentication backend for authenticating using Voter ID instead of username
    """
    
    def authenticate(self, request, voter_id=None, password=None, **kwargs):
        User = get_user_model()
        try:
            # Try to find a user by voter_id
            user = User.objects.get(voter_id=voter_id)
            
            # Check the password
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            # No user was found with the given voter_id
            return None
