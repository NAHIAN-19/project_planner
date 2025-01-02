from django.urls import path
from apps.tasks import views
from apps.tasks.views import (TaskListCreateView, TaskRetrieveUpdateDestroyView,
    CommentListCreateView, CommentDetailView
)

urlpatterns = [
    # Task URLs
    path('', TaskListCreateView.as_view(), name='task-list-create'),
    path('<int:pk>/', TaskRetrieveUpdateDestroyView.as_view(), name='task-retrieve-update-destroy'),
    path('status/change/<int:pk>/', views.TaskStatusChangeView.as_view(), name='task-status-change'),
    # Comment URLs
    path('comments/', CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    
    # Status Change Request URLs
    path('status/change/requests/', views.StatusChangeRequestListCreateView.as_view(), name='status-change-request-list-create'),
    path('status/change/requests/<int:pk>/', views.StatusChangeRequestRetrieveUpdateDestroyView.as_view(), name='status-change-request-retrieve-update-destroy'),
    path('status/change/requests/<int:pk>/action/', views.StatusChangeRequestAcceptRejectView.as_view(), name='accept-reject-status-change-request'),
    
]
