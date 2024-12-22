# Local imports
from apps.projects.models import Project, ProjectMembership
# django imports
from django.contrib.auth import get_user_model
# third-party imports
from rest_framework import serializers

# Get the custom User model
User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model to expose the user details.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'last_login']

class ProjectMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for the ProjectMembership model, exposing details about 
    the user and their project membership (joined date, total tasks, and completed tasks).
    """
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ['user', 'joined_at', 'total_tasks', 'completed_tasks']


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the Project model, exposing project details and related memberships.
    """
    owner = CustomUserSerializer(read_only=True)
    members = ProjectMembershipSerializer(source='memberships', many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'created_at', 
            'total_tasks', 'status', 'due_date', 'total_member_count', 
            'owner', 'members'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'total_tasks', 'total_member_count']


class ProjectCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new project. Handles adding members to the project.
    """
    members = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True)

    class Meta:
        model = Project
        fields = ['name', 'description', 'due_date', 'members']

    def create(self, validated_data):
        """
        Create a new project and add members, including the owner.
        """
        members = validated_data.pop('members', [])
        owner = self.context['request'].user
        # if owner id is in validated_data, remove it
        if 'owner' in validated_data:
            validated_data.pop('owner')
        # Create the project and assign the owner
        project = Project.objects.create(**validated_data, owner=owner)

        # Add the owner as a member
        ProjectMembership.objects.create(project=project, user=owner)

        # Add other members if not already the owner
        for user in members:
            if user != owner:
                ProjectMembership.objects.create(project=project, user=user)

        return project

    def to_representation(self, instance):
        """
        Override to use the ProjectSerializer for representation after creation.
        """
        return ProjectSerializer(instance).data


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating project details. Optionally updates the project's members.
    """
    members = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, required=False)

    class Meta:
        model = Project
        fields = ['name', 'description', 'due_date', 'status', 'members']

    def update(self, instance, validated_data):
        """
        Update the project fields and manage membership changes (add or remove members).
        """
        members = validated_data.pop('members', None)

        # Update the project fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If members data is provided, update the members
        if members is not None:
            current_members = set(instance.members.all())
            new_members = set(members)

            # Ensure the owner is not removed from the project
            if instance.owner not in new_members:
                new_members.add(instance.owner)

            # Remove members who are no longer part of the project
            to_remove = current_members - new_members
            ProjectMembership.objects.filter(project=instance, user__in=to_remove).delete()

            # Add new members to the project
            to_add = new_members - current_members
            for user in to_add:
                ProjectMembership.objects.create(project=instance, user=user)

        return instance
