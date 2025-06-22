from django.contrib import admin
from .models import Blockchain, Block, Transaction

@admin.register(Blockchain)
class BlockchainAdmin(admin.ModelAdmin):
    list_display = ('name', 'election', 'created_at', 'block_count')
    search_fields = ('name', 'election__name')
    readonly_fields = ('created_at', 'updated_at', 'block_count', 'genesis_block')
    
    def block_count(self, obj):
        return obj.blocks.count()
    
    block_count.short_description = 'Number of Blocks'

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('index', 'blockchain', 'timestamp', 'transactions_count')
    search_fields = ('index', 'blockchain__name')
    readonly_fields = ('previous_hash', 'hash', 'nonce', 'timestamp', 'merkle_root')
    list_filter = ('blockchain__name',)
    
    def transactions_count(self, obj):
        return obj.transactions.count()
    
    transactions_count.short_description = 'Number of Transactions'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'block', 'transaction_type', 'transaction_hash')
    search_fields = ('transaction_hash', 'voter_id', 'candidate_id')
    readonly_fields = ('timestamp', 'transaction_hash')
    list_filter = ('transaction_type', 'block__blockchain__name')
    
    def has_add_permission(self, request):
        # Transactions should only be added through the blockchain mechanism
        return False
    
    def has_change_permission(self, request, obj=None):
        # Transactions should be immutable
        return False

# Register the models with the custom admin site
from users.admin import django_admin_site

django_admin_site.register(Blockchain, BlockchainAdmin)
django_admin_site.register(Block, BlockAdmin)
django_admin_site.register(Transaction, TransactionAdmin)
