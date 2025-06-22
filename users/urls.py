from django.urls import path
# from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Location API endpoints
    path('constituencies/', views.get_constituencies, name='get_constituencies'),
    
    # API Authentication (placeholder for JWT)
    # path('api/token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Verification
    # path('api/verify/', views.VerifyVoterView.as_view(), name='api_verify'),
    # path('api/2fa/', views.TwoFactorAuthView.as_view(), name='api_2fa'),
    
    # Face recognition
    # path('api/face-verify/', views.FaceVerificationView.as_view(), name='api_face_verify'),
    
    # Admin
    # path('admin/voters/', views.AdminVoterListView.as_view(), name='admin_voters'),
]
