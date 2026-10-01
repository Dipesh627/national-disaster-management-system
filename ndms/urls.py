from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [

    # =====================================================
    # CUSTOM NDMS ADMIN PANEL
    # =====================================================

    path(
        'admin/',
        include('reports.admin_urls')
    ),

    # =====================================================
    # DJANGO INTERNAL ADMIN
    # =====================================================

    path(
        'django-admin/',
        admin.site.urls
    ),

    # =====================================================
    # USER / PUBLIC WEBSITE
    # =====================================================

    path(
        '',
        include('reports.urls')
    ),
]


if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )