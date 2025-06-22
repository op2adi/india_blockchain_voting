from django.urls import path
from . import views

app_name = 'blockchain'

urlpatterns = [
    # Blockchain API endpoints (commented out until views are implemented)
    # path('api/blocks/', views.BlockListView.as_view(), name='api_blocks'),
    # path('api/blocks/<int:block_id>/', views.BlockDetailView.as_view(), name='api_block_detail'),
    # path('api/chain/', views.ChainView.as_view(), name='api_chain'),
    # path('api/validate/', views.ValidateChainView.as_view(), name='api_validate'),
    # path('api/proof/<str:block_hash>/', views.ProofView.as_view(), name='api_proof'),
    
    # Mining endpoints
    # path('api/mine/', views.MineBlockView.as_view(), name='api_mine'),
    
    # Audit endpoints
    # path('api/audit/', views.AuditLogView.as_view(), name='api_audit'),
]
