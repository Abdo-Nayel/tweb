from django.conf import settings
from django.core.cache import cache


def shop_info(request):
    profile = cache.get('shop_profile')
    if profile is None:
        from .models import ShopProfile
        profile = ShopProfile.objects.first()
        cache.set('shop_profile', profile, 300)
    return {
        'shop': profile,
        'pharmacy': profile,  # legacy alias for templates not yet updated
        'static_version': settings.STATIC_VERSION,
        'project_name': settings.PROJECT_NAME,
        'project_vendor': settings.PROJECT_VENDOR,
        'currency_symbol': settings.CURRENCY_SYMBOL,
    }


# Legacy alias
pharmacy_info = shop_info
