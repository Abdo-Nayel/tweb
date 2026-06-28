from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.users.urls')),
    path('dashboard/', include('apps.pharmacy.urls')),
    path('settings/', include('apps.pharmacy.settings_urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('parties/', include('apps.parties.urls')),
    path('purchases/', include('apps.purchases.urls')),
    path('sales/', include('apps.sales.urls')),
    path('returns/', include('apps.returns.urls')),
    path('repairs/', include('apps.repairs.urls')),
    path('buyback/', include('apps.buyback.urls')),
    path('treasury/', include('apps.treasury.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
