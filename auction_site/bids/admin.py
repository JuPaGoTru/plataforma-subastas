from django.contrib import admin
from .models import Product, Bid, BannedIP

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'starting_price', 'current_price', 'start_time', 'end_time', 'status', 'is_active']
    list_filter = ['is_active', 'start_time', 'end_time', 'created_at']
    
    def status(self, obj):
        return obj.status
    status.short_description = 'Estado'

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['product', 'bidder', 'amount', 'created_at']
    list_filter = ['product', 'created_at']

    def bidder(self, obj):
        return obj.user.username if obj.user else obj.guest_user.username
    

@admin.register(BannedIP)
class BannedIPAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'added_at']
    list_filter = ['added_at']
    search_fields = ['ip_address']