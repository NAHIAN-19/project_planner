from django.urls import path
from apps.projects.views import (
    ProjectListCreateView, 
    ProjectRetrieveUpdateDestroyView, 
    MemberManageView
)

urlpatterns = [
    # Base URL: api/v1/projects/
    # Endpoint for listing projects and creating a new project
    path('', ProjectListCreateView.as_view(), name='project-list-create'),

    # Endpoint for retrieving, updating, or deleting a specific project by its primary key (pk)
    path('<int:pk>/', ProjectRetrieveUpdateDestroyView.as_view(), name='project-retrieve-update-destroy'),

    # Endpoint for managing project members (adding/removing members) for a specific project by its primary key (pk)
    path('<int:pk>/members/', MemberManageView.as_view(), name='project-member-manage'),
]
