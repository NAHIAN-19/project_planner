from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
)
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # App-specific URLs
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/projects/', include('apps.projects.urls')),
    # path('api/v1/tasks/', include('tasks.urls')),
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/payment/', include('payment.urls')),

    # DRF Spectacular Schema URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),  # OpenAPI Schema
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger UI
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  # ReDoc UI
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)