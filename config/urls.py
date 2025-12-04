"""
URL Configuration for Radio Occitania Pige System
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/recordings/', include('apps.recorder.urls')),
    path('api/archive/', include('apps.archive.urls')),
    path('api/ai/', include('apps.ai.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize admin
admin.site.site_header = "Radio Occitania - Système de Pige"
admin.site.site_title = "Pige Admin"
admin.site.index_title = "Administration du système de pige"
