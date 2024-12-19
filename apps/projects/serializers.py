from rest_framework import serializers
from .models import Project, ProjectMembership
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # Displays the user's username
    project = serializers.StringRelatedField()  # Displays the project's name

    class Meta:
        model = ProjectMembership
        fields = ['id', 'project', 'user', 'role']
        read_only_fields = ['project', 'user']

class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)  # Displays the owner's username
    members = serializers.SerializerMethodField()  # Fetch related members
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'start_date', 'status', 'end_date', 'owner', 'members']

    def get_members(self, obj):
        memberships = ProjectMembership.objects.filter(project=obj)
        return ProjectMembershipSerializer(memberships, many=True).data

    def create(self, validated_data):
        # Extract the members field
        members_data = validated_data.pop('members', [])
        # Create the project itself
        project = Project.objects.create(**validated_data)
        
        # Add the project owner (current user) as the first member
        owner = self.context['request'].user  # Assuming the user creating the project is the owner
        ProjectMembership.objects.create(
            project=project, 
            user=owner, 
            role='owner', 
            user_metadata=owner.metadata
        )
        
        # Add additional members, excluding the owner
        for user_id in members_data:
            user = User.objects.get(id=user_id)
            if user != owner:  # Avoid adding the owner again
                ProjectMembership.objects.create(
                    project=project,
                    user=user,
                    role='member',
                    user_metadata=user.metadata
                )

        return project

class ProjectMemberSerializer(serializers.Serializer):
    members = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )

    def validate_members(self, value):
        # Ensure the list is not empty
        if not value:
            raise serializers.ValidationError("At least one member must be provided.")
        return value

    def update_members(self, project, user_ids):
        # Add members
        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            
            # Check if user is already a member
            if ProjectMembership.objects.filter(project=project, user=user).exists():
                continue  # Skip if already a member
            
            # Create membership
            ProjectMembership.objects.create(project=project, user=user)
        
        return ProjectMembership.objects.filter(project=project, user__id__in=user_ids)