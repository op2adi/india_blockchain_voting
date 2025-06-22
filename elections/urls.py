from django.urls import path
from . import views

app_name = 'elections'

urlpatterns = [
    # Frontend pages
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('view-elections/', views.view_elections, name='view_elections'),
    path('vote/<int:election_id>/', views.vote_view, name='vote'),
    path('submit-vote/<int:election_id>/', views.submit_vote, name='submit_vote'),
    path('receipt/<uuid:vote_id>/', views.view_receipt, name='view_receipt'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('results/', views.results_view, name='results'),
    path('results/<int:election_id>/', views.results_view, name='results'),
    
    # API endpoints
    path('api/parties/', views.PartyListView.as_view(), name='api_parties'),
    path('api/candidates/', views.CandidateListView.as_view(), name='api_candidates'),
    path('api/vote/', views.CastVoteView.as_view(), name='api_vote'),
    path('api/leaderboard/', views.LeaderboardView.as_view(), name='api_leaderboard'),
    path('api/results/<int:election_id>/', views.ResultsView.as_view(), name='api_results'),
]
