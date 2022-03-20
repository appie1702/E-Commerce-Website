from django.contrib import admin
from .models import Item, OrderItem, Refund, Order, Address, Coupon
from django.contrib.auth import get_user_model


def refund_accepted_update(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


refund_accepted_update.short_description = "Update orders to refund granted"


class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'ordered',
        'paid',
        'being_delivered',
        'delivered',
        'refund_requested',
        'refund_granted',
        'billing_address',
        'shipping_address',
        'coupon'
    ]

    list_filter = [
        'ordered',
        'paid',
        'being_delivered',
        'delivered',
        'refund_requested',
        'refund_granted'
    ]

    list_display_links = [
        'user',
        'billing_address',
        'shipping_address',
        'coupon'
    ]

    search_fields = [
        'user__username',
        'ref_code'
    ]

    actions = [refund_accepted_update]


class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'address_line1',
        'address_line2',
        'country',
        'zip',
        'address_type',
        'default'
    ]

    list_filter = [
        'address_type',
        'default',
        'country'
    ]

    search_fields = [
        'user',
        'address_line1',
        'address_line2',
        'zip'
    ]

    actions = [refund_accepted_update]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'ordered']


admin.site.register(Item)
admin.site.register(Refund)
admin.site.register(Address, AddressAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Coupon)
