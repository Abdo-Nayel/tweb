from django.contrib import admin
from .models import Warehouse, ProductCategory, Brand, Product, StockLot, StockMovement

admin.site.register(Warehouse)
admin.site.register(ProductCategory)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(StockLot)
admin.site.register(StockMovement)
