from django.contrib import admin
from .models import ShopProfile, Branch, BarcodeLabelSettings, ReceiptSettings

admin.site.register(ShopProfile)
admin.site.register(Branch)
admin.site.register(BarcodeLabelSettings)
admin.site.register(ReceiptSettings)
