from django.urls import path
from . import admin_views

app_name = 'admin_elections'

urlpatterns = [
    # Election management
    path('start-voting/<int:election_id>/', admin_views.start_voting_view, name='start_voting'),
    path('stop-voting/<int:election_id>/', admin_views.stop_voting_view, name='stop_voting'),
    path('start-counting/<int:election_id>/', admin_views.start_counting_view, name='start_counting'),
    path('view-results/<int:election_id>/', admin_views.view_results_view, name='view_results'),
]
