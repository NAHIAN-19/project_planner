# Local Imports
from apps import subscriptions
from apps.projects.models import Project, ProjectMembership
from apps.projects.serializers import ProjectSerializer, ProjectMembershipSerializer, ProjectMemberSerializer
from apps.projects.permissions import IsProjectOwnerOrReadOnly
from apps.users.models import User
# django Imports
from django.db import models
from django.shortcuts import get_object_or_404
# Third Party Imports
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import permissions, status
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import serializers
@extend_schema(
    responses={200: ProjectSerializer(many=True)},
    parameters=[
        OpenApiParameter('owner', description='Filter by owner', type=str),
        OpenApiParameter('members', description='Filter by members', type=str)
    ]
)
class ProjectListCreateView(ListModelMixin,CreateModelMixin,GenericAPIView):
    """
    List all projects or create a new project.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrReadOnly]

    def get_queryset(self):
        """
        Return projects where the user is either the owner or a member.
        """
        user = self.request.user
        return Project.objects.filter(
            models.Q(owner=user) | 
            models.Q(members=user)
        ).distinct()

    def perform_create(self, serializer):
        """
        Custom save method to add the current user as the owner when creating the project.
        """
        user = self.request.user
        subscription = user.subscription
        plan = subscription.plan

        if plan.max_projects != -1 and user.profile.owned_projects_count >= plan.max_projects:
            raise serializers.ValidationError(
                f"Your plan allows a maximum of {plan.max_projects} projects. Upgrade your plan to create more projects."
            )

        serializer.save(owner=user)
        # Increment the owned projects count after saving
        user.profile.owned_projects_count += 1
        user.profile.save()

    @extend_schema(responses={201: ProjectSerializer})
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to list projects.
        """
        return self.list(request, *args, **kwargs)

    @extend_schema(responses={201: ProjectSerializer})
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create a new project.
        """
        return self.create(request, *args, **kwargs)


@extend_schema(
    responses={200: ProjectSerializer},
    request=ProjectSerializer
)
class ProjectRetrieveUpdateDestroyView(RetrieveModelMixin,UpdateModelMixin,DestroyModelMixin,GenericAPIView):
    """
    Retrieve, update or delete a project.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrReadOnly]

    @extend_schema(responses={200: ProjectSerializer})
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to retrieve a project.
        """
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(responses={200: ProjectSerializer})
    def patch(self, request, *args, **kwargs):
        """
        Handle PATCH request to partially update a project.
        """
        return self.partial_update(request, *args, **kwargs)

    @extend_schema(responses={204: OpenApiResponse(description="Project deleted")})
    def delete(self, request, *args, **kwargs):
        """
        Handle DELETE request to remove a project.
        """
        project = kwargs.get('pk')
        project = get_object_or_404(Project, pk=project)
        owner_subscription = project.owner.subscription
        plan = owner_subscription.plan

        # Validate members count before deletion
        if plan.max_members_per_project != -1 and ProjectMembership.objects.filter(project=project).count() <= 0:
            raise serializers.ValidationError("You cannot have fewer members than allowed in the plan.")
        return self.destroy(request, *args, **kwargs)


@extend_schema(
    responses={200: ProjectMemberSerializer(many=True)},
    parameters=[OpenApiParameter('project_id', description='Project ID to manage members', type=int)]
)
class ManageMembersView(CreateModelMixin,DestroyModelMixin,GenericAPIView):
    """
    Manage project members: Add or remove members.
    """
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrReadOnly]

    @extend_schema(responses={201: 'Members added successfully'})
    def post(self, request):
        """
        Add or remove members based on the action provided in the request.
        """
        project_id = request.data.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        members_data = request.data.get('members', [])

        # Validate the provided member data
        serializer = ProjectMemberSerializer(data={'members': members_data})
        if serializer.is_valid():
            if 'add' in request.data.get('action', ''):  # Add members
                self.create(request, pk=project_id)
                return Response({'message': 'Members added successfully'}, status=status.HTTP_201_CREATED)

            elif 'remove' in request.data.get('action', ''):  # Remove members
                self.destroy(request, pk=project_id)
                return Response({'message': 'Members removed successfully'}, status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        """
        Optionally override to customize the queryset for listing or processing memberships.
        """
        return ProjectMembership.objects.all()

    def create(self, request, pk=None):
        """
        Custom logic for adding members.
        """
        project = get_object_or_404(Project, pk=pk)
        members_data = request.data.get('members', [])
        subscriptions = project.owner.subscription
        plan = subscriptions.plan
        current_member_count = ProjectMembership.objects.filter(project=project).count()
        new_members = len(members_data)
        # Add members
        if plan.max_members_per_project != -1 and (current_member_count + new_members) > plan.max_members_per_project:
            raise serializers.ValidationError(
                f"Your plan allows a maximum of {plan.max_members_per_project} members per project. Upgrade your plan to add more members."
            )
        for user_id in members_data:
            user = get_object_or_404(User, id=user_id)

            # Skip if user is already a member
            if not ProjectMembership.objects.filter(project=project, user=user).exists():
                ProjectMembership.objects.create(project=project, user=user, user_metadata=user.metadata)

    def destroy(self, request, pk=None):
        """
        Custom logic for removing members.
        """
        project = get_object_or_404(Project, pk=pk)
        members_data = request.data.get('members', [])

        # Remove members
        for user_id in members_data:
            membership = ProjectMembership.objects.filter(project=project, user_id=user_id)
            if membership.exists():
                membership.delete()


@extend_schema(
    responses={200: ProjectMembershipSerializer(many=True)},
    parameters=[OpenApiParameter('user_id', description='Filter memberships by user', type=int)]
)
class ProjectMembershipListCreateView(ListModelMixin,CreateModelMixin,GenericAPIView):
    """
    List all project memberships or create a new membership.
    """
    serializer_class = ProjectMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return memberships where the user is either the project owner or a member.
        """
        user = self.request.user
        return ProjectMembership.objects.filter(
            models.Q(project__owner=user) | 
            models.Q(project__members=user)
        ).distinct()

    @extend_schema(responses={200: ProjectMembershipSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to list memberships.
        """
        return self.list(request, *args, **kwargs)

    @extend_schema(responses={201: ProjectMembershipSerializer})
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create a new membership.
        """
        return self.create(request, *args, **kwargs)


@extend_schema(
    responses={200: ProjectMembershipSerializer},
    request=ProjectMembershipSerializer
)
class ProjectMembershipRetrieveUpdateDestroyView(RetrieveModelMixin,UpdateModelMixin,DestroyModelMixin,GenericAPIView):
    """
    Retrieve, update or delete a project membership.
    """
    queryset = ProjectMembership.objects.all()
    serializer_class = ProjectMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: ProjectMembershipSerializer})
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to retrieve a project membership.
        """
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(responses={200: ProjectMembershipSerializer})
    def put(self, request, *args, **kwargs):
        """
        Handle PUT request to update a project membership.
        """
        return self.update(request, *args, **kwargs)

    @extend_schema(responses={204: OpenApiResponse(description="Membership deleted")})
    def delete(self, request, *args, **kwargs):
        """
        Handle DELETE request to remove a project membership.
        """
        return self.destroy(request, *args, **kwargs)