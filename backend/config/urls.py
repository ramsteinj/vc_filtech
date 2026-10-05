from django.conf import settings
from django.conf.urls.static import static

# API routes are added per phase under /api/ (specs/10-api.md).
urlpatterns = []

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
