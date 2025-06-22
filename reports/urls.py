from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Report generation
    path('vote-receipt/<str:vote_id>/', views.generate_vote_receipt, name='vote_receipt'),
    path('download-receipt/<str:receipt_id>/', views.download_receipt, name='download_receipt'),
    path('election-report/<int:election_id>/', views.election_report, name='election_report'),
    path('audit-report/<int:blockchain_id>/', views.audit_report, name='audit_report'),
    
    # API endpoints
    path('api/receipt/<str:vote_id>/', views.VoteReceiptAPI.as_view(), name='api_vote_receipt'),
    path('api/election-stats/<int:election_id>/', views.ElectionStatsAPI.as_view(), name='api_election_stats'),
]
