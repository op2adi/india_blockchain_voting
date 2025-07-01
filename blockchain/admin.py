from django.contrib import admin
from .models import Blockchain, Block, VoteTransaction, BlockchainAuditLog, GenesisBlock, Transaction

# Define admin classes but don't register with default admin site yet
class BlockchainAdmin(admin.ModelAdmin):
    list_display = ('name', 'election_id', 'created_at', 'block_count')
    search_fields = ('name', 'election_id')
    readonly_fields = ('name', 'genesis_hash', 'latest_hash', 'difficulty', 'total_blocks', 'election_id', 'is_active', 'created_at', 'updated_at')
    
    def block_count(self, obj):
        return obj.total_blocks
    
    block_count.short_description = 'Number of Blocks'
    
    def has_add_permission(self, request):
        # Blockchains should only be created through the election creation process
        return False
    
    def has_change_permission(self, request, obj=None):
        # Only certain fields should be editable, and only by system processes
        return False

class BlockAdmin(admin.ModelAdmin):
    list_display = ('index', 'hash', 'timestamp', 'transactions_count')
    search_fields = ('index', 'hash')
    readonly_fields = ('index', 'data', 'previous_hash', 'hash', 'nonce', 'timestamp', 'merkle_root', 'is_valid', 'validator_signature')
    
    def transactions_count(self, obj):
        return obj.transactions.count()
    
    transactions_count.short_description = 'Number of Transactions'
    
    def has_add_permission(self, request):
        # Blocks should only be added through the blockchain mechanism, not manually
        return False
    
    def has_change_permission(self, request, obj=None):
        # Blocks should be immutable
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Blocks should not be deletable
        return False

class VoteTransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'block', 'transaction_hash')
    search_fields = ('transaction_hash', 'voter_id')
    readonly_fields = ('timestamp', 'transaction_hash')
    list_filter = ('is_confirmed',)
    
    def has_add_permission(self, request):
        # Transactions should only be added through the blockchain mechanism
        return False
    
    def has_change_permission(self, request, obj=None):
        # Transactions should be immutable
        return False

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'amount', 'timestamp')
    search_fields = ('sender', 'recipient')
    readonly_fields = ('timestamp',)

class BlockchainAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'blockchain', 'actor_type', 'timestamp', 'success')
    search_fields = ('action', 'actor_id')
    list_filter = ('action', 'success', 'actor_type')
    readonly_fields = ('timestamp', 'execution_time')

class GenesisBlockAdmin(admin.ModelAdmin):
    list_display = ('blockchain', 'genesis_timestamp')
    search_fields = ('blockchain__name',)
    readonly_fields = ('genesis_timestamp', 'created_at')

# Register the models with the custom admin site
from users.admin import django_admin_site

django_admin_site.register(Blockchain, BlockchainAdmin)
django_admin_site.register(Block, BlockAdmin)
django_admin_site.register(VoteTransaction, VoteTransactionAdmin)
django_admin_site.register(Transaction, TransactionAdmin)
django_admin_site.register(BlockchainAuditLog, BlockchainAuditLogAdmin)
django_admin_site.register(GenesisBlock, GenesisBlockAdmin)
