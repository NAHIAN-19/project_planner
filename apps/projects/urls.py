from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectRetrieveUpdateDestroyView,
    ManageMembersView,
    ProjectMembershipListCreateView,
    ProjectMembershipRetrieveUpdateDestroyView
)

urlpatterns = [
    # Base URL: /api/v1/projects/
    # Endpoint to list all projects the user is part of or owns, and to create new projects
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    
    # Endpoint to retrieve details of a specific project by its ID, update its information, or delete it
    path('<int:pk>/', ProjectRetrieveUpdateDestroyView.as_view(), name='project-detail'),
    
    # Endpoint to manage members of a project (add or remove members)
    path('members/', ManageMembersView.as_view(), name='project-manage-member'),
    
    # Endpoint to list all project memberships the user is involved in or to create a new membership
    path('memberships/', ProjectMembershipListCreateView.as_view(), name='project-membership-list-create'),
    
    # Endpoint to retrieve details of a specific project membership by its ID, update it, or delete it
    path('memberships/<int:pk>/', ProjectMembershipRetrieveUpdateDestroyView.as_view(), name='project-membership-detail'),
]
