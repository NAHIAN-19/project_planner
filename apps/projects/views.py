# Local imports
from apps import subscriptions
from apps.projects.models import Project, ProjectMembership
from apps.projects.serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectMembershipSerializer, ProjectUpdateSerializer
)
# django imports
from django.db.models import Prefetch
from django.contrib.auth import get_user_model
# third-party imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

# Get the custom user model
User = get_user_model()

def standardized_response(status_code, status_message, message, data=None):
    """
    Utility to create standardized API responses.
    """
    response = {
        "status": status_message,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    return Response(response, status=status_code)

class ProjectListCreateView(ListCreateAPIView):
    """
    API view to list all projects for the authenticated user and create a new project.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the HTTP method.
        """
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer

    def get_queryset(self):
        """
        Return the list of projects that the authenticated user is a member of.
        """
        user = self.request.user
        return Project.objects.filter(
            memberships__user=user
        ).select_related('owner').prefetch_related(
            Prefetch('memberships', queryset=ProjectMembership.objects.select_related('user'))
        ).distinct()

    @extend_schema(
        summary="List and Create Projects",
        description="Get a list of all projects for the authenticated user or create a new project.",
        responses={
            200: ProjectSerializer(many=True),
            201: ProjectSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Handle project creation.
        """
        response = super().post(request, *args, **kwargs)
        return standardized_response(
            status_code=response.status_code,
            status_message="success" if response.status_code == 201 else "error",
            message="Project created successfully." if response.status_code == 201 else "Failed to create project.",
            data=response.data
        )

    def perform_create(self, serializer):
        """
        Perform the creation of the project and assign the current user as the owner.
        """
        user = self.request.user
        subscription = user.subscription
        plan = subscription.plan if subscription else None
        if plan and plan.max_projects != 1 and plan.max_projects <= user.profile.owned_projects_count:
            raise ValidationError(
                f"Your plan allows a maximum of {plan.max_projects} projects. Upgrade your plan to create more projects."
            )
        serializer.save(owner=self.request.user)
        user.profile.owned_projects_count += 1
        user.profile.save()

class ProjectRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete a specific project.
    """
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the HTTP method.
        """
        if self.request.method in ['PUT', 'PATCH']:
            return ProjectUpdateSerializer
        return ProjectSerializer

    def get_queryset(self):
        """
        Return the project details with memberships and owner info.
        """
        return Project.objects.select_related('owner').prefetch_related(
            Prefetch('memberships', queryset=ProjectMembership.objects.select_related('user'))
        )

    @extend_schema(
        summary="Retrieve, Update or Delete a Project",
        description="Get details of a specific project, update its information, or delete it.",
        responses={
            200: ProjectSerializer,
            204: None,
        }
    )
    def put(self, request, *args, **kwargs):
        """
        Handle project update.
        """
        response = super().put(request, *args, **kwargs)
        return standardized_response(
            status_code=response.status_code,
            status_message="success",
            message="Project updated successfully.",
            data=response.data
        )

    @extend_schema(
        summary="Partially Update a Project",
        description="Update partial information of a specific project.",
        responses={
            200: ProjectSerializer,
        }
    )
    def patch(self, request, *args, **kwargs):
        """
        Handle partial project update.
        """
        response = super().patch(request, *args, **kwargs)
        return standardized_response(
            status_code=response.status_code,
            status_message="success",
            message="Project partially updated successfully.",
            data=response.data
        )

    @extend_schema(
        summary="Delete a Project",
        description="Delete a specific project.",
        responses={
            204: None,
        }
    )
    def delete(self, request, *args, **kwargs):
        """
        Handle project deletion.
        """
        response = super().delete(request, *args, **kwargs)
        return standardized_response(
            status_code=status.HTTP_204_NO_CONTENT,
            status_message="success",
            message="Project deleted successfully."
        )

    def perform_update(self, serializer):
        """
        Ensure that only the project owner can update the project.
        """
        project = serializer.instance
        if self.request.user != project.owner:
            raise PermissionDenied("Only the project owner can update this project.")
        serializer.save()

class MemberManageView(GenericAPIView):
    """
    API view to manage members in a specific project (add or remove members).
    """
    serializer_class = ProjectMembershipSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add Members to Project",
        description="Add one or more users as members to a specific project.",
        request={'application/json': {'user_ids': [1, 2, 3]}},
        responses={
            200: OpenApiExample(
                'Successful Response',
                value={
                    'status': 'success',
                    'message': 'Member management completed.',
                    'added_users': ['user1', 'user2'],
                    'already_members': ['user3']
                },
                response_only=True,
            ),
            403: OpenApiExample(
                'Forbidden',
                value={'status': 'error', 'message': 'You do not have permission to manage this project.'},
                response_only=True,
            ),
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Add members to a project.
        """
        project_id = kwargs.get('pk')
        user_ids = request.data.get('user_ids', [])
        project = Project.objects.filter(id=project_id, owner=request.user).first()

        if not project:
            return standardized_response(
                status_code=status.HTTP_403_FORBIDDEN,
                status_message="error",
                message="You do not have permission to manage this project."
            )

        added_users = []
        already_members = []
        for user_id in user_ids:
            user = User.objects.filter(id=user_id).first()
            if user:
                membership, created = ProjectMembership.objects.get_or_create(project=project, user=user)
                if created:
                    added_users.append(user.username)
                else:
                    already_members.append(user.username)

        return standardized_response(
            status_code=status.HTTP_200_OK,
            status_message="success",
            message="Member management completed.",
            data={
                "added_users": added_users,
                "already_members": already_members
            }
        )

    @extend_schema(
        summary="Remove Members from Project",
        description="Remove one or more users from a specific project.",
        request={'application/json': {'user_ids': [1, 2, 3]}},
        responses={
            200: OpenApiExample(
                'Successful Response',
                value={
                    'status': 'success',
                    'message': 'Member removal completed.',
                    'removed_users': ['user1', 'user2'],
                    'not_found_users': ['user3']
                },
                response_only=True,
            ),
            400: OpenApiExample(
                'Bad Request',
                value={'status': 'error', 'message': 'Cannot remove the project owner from members.'},
                response_only=True,
            ),
            403: OpenApiExample(
                'Forbidden',
                value={'status': 'error', 'message': 'You do not have permission to manage this project.'},
                response_only=True,
            ),
        }
    )
    def delete(self, request, *args, **kwargs):
        """
        Remove members from a project.
        """
        project_id = kwargs.get('pk')
        user_ids = request.data.get('user_ids', [])
        project = Project.objects.filter(id=project_id, owner=request.user).first()

        if not project:
            return standardized_response(
                status_code=status.HTTP_403_FORBIDDEN,
                status_message="error",
                message="You do not have permission to manage this project."
            )

        # Ensure owner is not in the list of users to be removed
        if project.owner.id in user_ids:
            return standardized_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                status_message="error",
                message="Cannot remove the project owner from members."
            )

        removed_users = []
        not_found_users = []
        for user_id in user_ids:
            membership = ProjectMembership.objects.filter(project=project, user_id=user_id).first()
            if membership:
                username = membership.user.username
                membership.delete()
                removed_users.append(username)
            else:
                user = User.objects.filter(id=user_id).first()
                not_found_users.append(user.username if user else f"UserID:{user_id}")

        return standardized_response(
            status_code=status.HTTP_200_OK,
            status_message="success",
            message="Member removal completed.",
            data={
                "removed_users": removed_users,
                "not_found_users": not_found_users
            }
        )
