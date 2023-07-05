from django.contrib import admin
from .models import Payment, Order, OrderProduct
# Register your models here.

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'user', 'payment_method', 'amount_paid', 'status')


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'quantity', 'product_price', 'ordered')
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ( 'order_number', 'user', 'payment', 'full_name', 'phone', 'email', 'country', 'city', 'state', 'full_address', 'order_total', 'status', 'ip', 'is_ordered', 'updated_at')
    list_filter = ('user', 'country', 'city', 'state', 'status', 'is_ordered')
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    
    inlines = [OrderProductInline]
    
    
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)