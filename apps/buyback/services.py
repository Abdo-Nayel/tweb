"""مساعد إنشاء منتج من شاشة شراء فرد."""
from decimal import Decimal

from django.shortcuts import get_object_or_404

from apps.core.codes import next_serial
from apps.inventory.models import Brand, Product, ProductCategory


def create_product_from_buyback(post, user, purchase_amount, sale_price):
    category = get_object_or_404(ProductCategory, pk=post['new_category'], is_active=True)
    brand = get_object_or_404(Brand, pk=post['new_brand'], is_active=True)

    model_name = post.get('model_name', '').strip()
    storage = post.get('storage', '').strip()
    color = post.get('color', '').strip()
    name = post.get('new_product_name', '').strip()
    if not name:
        parts = [brand.name, model_name, storage, color]
        name = ' — '.join(p for p in parts if p) or 'جهاز مستعمل'

    return Product.objects.create(
        sku=next_serial(Product, 'sku'),
        name=name,
        category=category,
        brand=brand,
        model_name=model_name,
        storage=storage,
        color=color,
        condition=Product.Condition.USED,
        is_serialized=True,
        cost_price=purchase_amount,
        sale_price=sale_price or Decimal('0'),
        notes=post.get('device_specs', '').strip(),
        created_by=user,
    )
