from django.urls import path
from apps.notifications.views import (
    NotificationListCreateView,
    NotificationRetrieveUpdateDestroyView,
    NotificationPreferenceRetrieveUpdateDestroyView,
)

urlpatterns = [
    # Base url : /api/v1/notifications/
    path('', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('<int:pk>/', NotificationRetrieveUpdateDestroyView.as_view(), name='notification-detail'),
    path('preferences/', NotificationPreferenceRetrieveUpdateDestroyView.as_view(), name='notification-preference'),
]
