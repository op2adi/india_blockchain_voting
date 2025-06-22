from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Middleware to check if a user is logged in and redirect to login page if not.
    """
    
    def process_request(self, request):
        # Paths that don't require login
        open_paths = [
            reverse('users:login'),
            reverse('users:register'),
            reverse('users:logout'),
        ]
        
        # Check if the user is authenticated
        if not request.user.is_authenticated and request.path not in open_paths and not request.path.startswith('/admin/'):
            return redirect('users:login')
        
        return None
