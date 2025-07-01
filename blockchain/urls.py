from django.urls import path
from . import views
from . import views_new  # Import views_new for missing classes
from blockchain.network import api as network_api

app_name = 'blockchain'

urlpatterns = [
    # Blockchain API endpoints
    path('api/blocks/', views_new.BlockListView.as_view(), name='api_blocks'),
    path('api/blocks/<int:block_id>/', views_new.BlockDetailView.as_view(), name='api_block_detail'),
    path('api/chain/', views_new.ChainView.as_view(), name='api_chain'),
    path('api/validate/', views_new.ValidateChainView.as_view(), name='api_validate'),
    path('api/proof/<str:block_hash>/', views_new.ProofView.as_view(), name='api_proof'),
    
    # Mining endpoints
    path('api/mine/', views_new.MineBlockView.as_view(), name='api_mine'),
    
    # Audit endpoints
    path('api/audit/', views_new.AuditLogView.as_view(), name='api_audit'),
    
    # P2P Network API endpoints
    path('api/network/nodes/', network_api.NodeListView.as_view(), name='nodes_list'),
    path('api/network/nodes/register/', network_api.NodeRegisterView.as_view(), name='register_node'),
    path('api/network/consensus/', network_api.BlockchainConsensusView.as_view(), name='consensus'),
    path('api/network/status/', network_api.NodeStatusView.as_view(), name='node_status'),
    path('api/chain/<int:blockchain_id>/', network_api.ChainView.as_view(), name='get_chain'),
    path('api/receive_block/', network_api.ReceiveBlockView.as_view(), name='receive_block'),
]
