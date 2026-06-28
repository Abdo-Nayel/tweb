from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pharmacy'
    verbose_name = 'إعدادات المحل'

    def ready(self):
        if getattr(PharmacyConfig, '_sqlite_pragmas', False):
            return
        PharmacyConfig._sqlite_pragmas = True

        from django.core.cache import cache
        from django.db.backends.signals import connection_created
        from django.db.models.signals import post_save, post_delete
        from django.dispatch import receiver
        from .models import ShopProfile

        @receiver(connection_created)
        def setup_sqlite(sender, connection, **kwargs):
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA journal_mode=WAL;')
                    cursor.execute('PRAGMA synchronous=NORMAL;')
                    cursor.execute('PRAGMA cache_size=-64000;')

        @receiver([post_save, post_delete], sender=ShopProfile)
        def clear_shop_cache(sender, **kwargs):
            cache.delete('shop_profile')
            cache.delete('pharmacy_profile')
