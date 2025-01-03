# local imports
from apps.projects.models import Project, ProjectMembership
from apps.projects.serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectUpdateSerializer,
    DetailedProjectMembershipSerializer, ProjectListSerializer
)
from apps.projects.filters import ProjectFilter
from apps.notifications.utils import send_real_time_notification
# django imports
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import reverse
# third party imports
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response


@extend_schema_view(
    # Define schema for the `list` method
    list=extend_schema(
        summary='List Projects',  # Brief summary of the method
        description='Retrieve a list of projects owned by the authenticated user.',  # Detailed description
        parameters=[
            # Define parameters for filtering, searching, and ordering projects
            OpenApiParameter(name='name', description='Filter projects by name', type=str),
            OpenApiParameter(name='status', description='Filter projects by status', type=str),
            OpenApiParameter(name='due_date', description='Filter projects by due date', type=str),
            OpenApiParameter(name='search', description='Search projects by name or description', type=str),
            OpenApiParameter(name='ordering', description='Order projects by field (e.g. name, -created_at)', type=str),
        ],
        responses={
            200: ProjectListSerializer(many=True),  # Response for successful retrieval
            400: OpenApiExample(
                'Bad Request',  # Example for invalid filter parameters
                value={'error': 'Invalid filter parameter'},
                status_codes=['400']
            ),
        }
    ),
    # Define schema for the `create` method
    create=extend_schema(
        summary='Create a New Project',  # Brief summary of the method
        description='Create a new project and assign members to it. Sends notifications to the assigned members.',  # Detailed description
        request=ProjectCreateSerializer,  # Serializer used for input validation
        responses={
            201: ProjectSerializer,  # Response for successful creation
            400: OpenApiExample(
                'Bad Request',  # Example for invalid data
                value={'error': 'Invalid data provided'},
                status_codes=['400']
            ),
            403: OpenApiExample(
                'Forbidden',  # Example for exceeding project limits
                value={'error': 'Maximum project limit reached for your plan'},
                status_codes=['403']
            ),
        }
    )
)
class ProjectListCreateView(generics.ListCreateAPIView):
    # Specify authentication requirement
    permission_classes = [permissions.IsAuthenticated]
    # Queryset for fetching projects
    queryset = Project.objects.all()
    # Enable filtering, searching, and ordering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter  # Custom filter class
    search_fields = ['name', 'description']  # Fields to search
    ordering_fields = ['name', 'created_at', 'due_date', 'status']  # Fields to order
    ordering = ['-created_at']  # Default ordering

    def get_serializer_class(self):
        # Determine serializer based on HTTP method
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectListSerializer

    def get_queryset(self):
        # Fetch projects either owned by or shared with the user
        user = self.request.user
        return Project.objects.select_related(
            'owner'  # Optimize query for project owner
        ).prefetch_related(
            'memberships__user',  # Optimize for project members
            'tasks'  # Optimize for related tasks
        ).filter(
            Q(owner=user) |  # Projects owned by user
            Q(memberships__user=user)  # Projects where user is a member
        ).distinct()

    def create(self, request, *args, **kwargs):
        # Handle project creation with validations
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)  # Validate input data
            self.perform_create(serializer)  # Save the project
            headers = self.get_success_headers(serializer.data)  # Generate headers
            return Response({
                "message": "Project created successfully.",
                "code": status.HTTP_201_CREATED,
                "data": serializer.data  # Include serialized project data
            }, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            # Handle validation errors
            return Response({
                "message": "Failed to create project.",
                "code": status.HTTP_400_BAD_REQUEST,
                "data": {"error": str(e)}  # Include error details
            }, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        # Perform additional checks before saving the project
        user = self.request.user
        subscription = user.subscription
        plan = subscription.plan if subscription else None
        if plan and plan.max_projects != -1 and plan.max_projects <= user.profile.owned_projects_count:
            # Check if the user has exceeded their plan's project limit
            raise ValidationError(
                f"Your plan allows a maximum of {plan.max_projects} projects. Upgrade your plan to create more projects."
            )
        # Save the project and associate it with the owner
        project = serializer.save(owner=self.request.user)
        user.profile.owned_projects_count += 1  # Increment the owner's project count
        user.profile.save()

        members = serializer.validated_data.get('members', [])  # Get project members
        request = self.request
        # Notify members about their assignment to the project
        for member in members:
            send_real_time_notification(
                user=member,
                message={
                    "title": "New Project Assigned",
                    "body": f"You have been added to the project '{project.name}'.",
                    "url": request.build_absolute_uri(reverse('project-retrieve-update-destroy', kwargs={'pk': project.id}))
                },
                notification_type="project",  # Notification type
                content_type=ContentType.objects.get_for_model(Project).id,  # Reference model
                object_id=project.id  # Reference project
            )

    def list(self, request, *args, **kwargs):
        # Handle listing of projects
        queryset = self.filter_queryset(self.get_queryset())  # Apply filters
        page = self.paginate_queryset(queryset)  # Paginate results
        if page is not None:
            # If pagination is enabled, include paginated response
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                "message": "Projects retrieved successfully.",
                "code": status.HTTP_200_OK,
                "data": serializer.data
            })

        # Return all results if pagination is not enabled
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Projects retrieved successfully.",
            "code": status.HTTP_200_OK,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    retrieve=extend_schema(
        summary='Retrieve a Project',
        description='Retrieve detailed information about a specific project owned by the authenticated user.',
        responses={
            200: ProjectSerializer,
            404: OpenApiExample(
                'Not Found',
                value={"message": "Project not found", "code": 404, "data": None},
                status_codes=['404']
            ),
        }
    ),
    update=extend_schema(
        summary='Update a Project',
        description='Update an existing project. Sends notifications to new and removed members.',
        request=ProjectUpdateSerializer,
        responses={
            200: ProjectSerializer,
            400: OpenApiExample(
                'Bad Request',
                value={"message": "Invalid data provided", "code": 400, "data": None},
                status_codes=['400']
            ),
            403: OpenApiExample(
                'Forbidden',
                value={"message": "You do not have permission to update this project", "code": 403, "data": None},
                status_codes=['403']
            ),
            404: OpenApiExample(
                'Not Found',
                value={"message": "Project not found", "code": 404, "data": None},
                status_codes=['404']
            ),
        }
    ),
    partial_update=extend_schema(
        summary='Partially Update a Project',
        description='Partially update an existing project. Sends notifications to new and removed members.',
        request=ProjectUpdateSerializer,
        responses={
            200: ProjectSerializer,
            400: OpenApiExample(
                'Bad Request',
                value={"message": "Invalid data provided", "code": 400, "data": None},
                status_codes=['400']
            ),
            403: OpenApiExample(
                'Forbidden',
                value={"message": "You do not have permission to update this project", "code": 403, "data": None},
                status_codes=['403']
            ),
            404: OpenApiExample(
                'Not Found',
                value={"message": "Project not found", "code": 404, "data": None},
                status_codes=['404']
            ),
        }
    ),
    destroy=extend_schema(
        summary='Delete a Project',
        description='Delete a project. Only the owner can delete the project.',
        responses={
            204: OpenApiExample(
                'No Content',
                value={"message": "Project successfully deleted", "code": 204, "data": None},
                status_codes=['204']
            ),
            403: OpenApiExample(
                'Forbidden',
                value={"message": "You do not have permission to delete this project", "code": 403, "data": None},
                status_codes=['403']
            ),
            404: OpenApiExample(
                'Not Found',
                value={"message": "Project not found", "code": 404, "data": None},
                status_codes=['404']
            ),
        }
    )
)
class ProjectRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    # Permission is restricted to authenticated users only.
    permission_classes = [permissions.IsAuthenticated]
    
    # Base queryset for retrieving projects.
    queryset = Project.objects.all()

    def get_serializer_class(self):
        # Determine the serializer class based on the request method.
        if self.request.method in ['PUT', 'PATCH']:
            return ProjectUpdateSerializer
        return ProjectSerializer

    def get_queryset(self):
        # Fetch the authenticated user.
        user = self.request.user
        
        # Use optimized queries to fetch projects owned by or shared with the user.
        return Project.objects.select_related(
            'owner'  # Fetch project owner details in a single query.
        ).prefetch_related(
            'memberships__user',  # Fetch related users in project memberships.
            'tasks'  # Fetch related tasks.
        ).filter(
            Q(owner=user) |  # Projects owned by the user.
            Q(memberships__user=user)  # Projects where the user is a member.
        ).distinct()  # Remove duplicate projects.

    def update(self, request, *args, **kwargs):
        # Perform a partial or full update based on the request parameters.
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # Fetch the specific project instance.
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({
                "message": "Project updated successfully.",
                "code": status.HTTP_200_OK,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            # Handle validation errors gracefully.
            return Response({
                "message": "Failed to update project.",
                "code": status.HTTP_400_BAD_REQUEST,
                "data": {"error": str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            # Handle permission denial errors.
            return Response({
                "message": "Permission denied.",
                "code": status.HTTP_403_FORBIDDEN,
                "data": {"error": str(e)}
            }, status=status.HTTP_403_FORBIDDEN)

    def perform_update(self, serializer):
        # Ensure that only the project owner can perform updates.
        if serializer.instance.owner != self.request.user:
            raise PermissionDenied("Only the project owner can update the project.")
        
        # Save the updated project instance.
        updated_project = serializer.save()
        
        # Fetch new and removed members for notification.
        new_members = serializer.context.get('new_members', [])
        removed_members = serializer.context.get('removed_members', [])
        request = self.request

        # Send notifications to newly added members.
        if new_members:
            for member in new_members:
                send_real_time_notification(
                    user=member,
                    message={
                        "title": "New Project Assigned",
                        "body": f"You have been added to the project '{updated_project.name}'.",
                        "url": request.build_absolute_uri(reverse('project-retrieve-update-destroy', kwargs={'pk': updated_project.id}))
                    },
                    notification_type="project",
                    content_type=ContentType.objects.get_for_model(Project).id,
                    object_id=updated_project.id
                )

        # Notify removed members about their removal.
        if removed_members:
            for member in removed_members:
                send_real_time_notification(
                    user=member,
                    message={
                        "title": "Project Removed",
                        "body": f"You have been removed from the project '{updated_project.name}'.",
                        "url": request.build_absolute_uri(reverse('project-list-create'))
                    },
                    notification_type="project",
                    content_type=ContentType.objects.get_for_model(Project).id,
                    object_id=updated_project.id
                )

    def destroy(self, request, *args, **kwargs):
        # Handle project deletion.
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response({
                "message": "Project successfully deleted.",
                "code": status.HTTP_204_NO_CONTENT,
                "data": None
            }, status=status.HTTP_204_NO_CONTENT)
        except PermissionDenied as e:
            # Handle permission denial errors for deletion.
            return Response({
                "message": "Permission denied.",
                "code": status.HTTP_403_FORBIDDEN,
                "data": {"error": str(e)}
            }, status=status.HTTP_403_FORBIDDEN)

    def perform_destroy(self, instance):
        # Ensure that only the project owner can delete the project.
        if instance.owner != self.request.user:
            raise PermissionDenied("Only the project owner can delete the project.")
        instance.delete()  # Delete the project instance.



@extend_schema_view(
    retrieve=extend_schema(
        summary='Retrieve Project Membership Details',
        description='Retrieve detailed information about a user\'s membership in a project.',
        responses={
            200: DetailedProjectMembershipSerializer,  # Successful response with detailed membership information.
            404: OpenApiExample(
                'Not Found',
                value={"message": "Project membership not found", "code": 404, "data": None},
                status_codes=['404']  # Response when the membership is not found.
            ),
        }
    )
)
class ProjectMembershipView(generics.RetrieveAPIView):
    # Restrict access to authenticated users only.
    permission_classes = [permissions.IsAuthenticated]

    # Base queryset for retrieving project memberships.
    queryset = ProjectMembership.objects.all()

    # Serializer to use for detailed membership representation.
    serializer_class = DetailedProjectMembershipSerializer

    # Use the 'id' field to look up the membership instance.
    lookup_field = 'id'

    def get_queryset(self):
        # Restrict the queryset to memberships associated with the authenticated user.
        # This ensures users can only access their own membership details.
        return ProjectMembership.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            # Attempt to fetch the specific membership instance using the lookup field.
            instance = self.get_object()

            # Serialize the instance to return the detailed membership data.
            serializer = self.get_serializer(instance)
            return Response({
                "message": "Project membership retrieved successfully.",  # Success message.
                "code": status.HTTP_200_OK,  # HTTP 200 status code.
                "data": serializer.data  # Serialized membership data.
            }, status=status.HTTP_200_OK)
        except ProjectMembership.DoesNotExist:
            # Handle the case where the membership does not exist.
            return Response({
                "message": "Project membership not found.",  # Error message.
                "code": status.HTTP_404_NOT_FOUND,  # HTTP 404 status code.
                "data": None  # No additional data to return.
            }, status=status.HTTP_404_NOT_FOUND)
