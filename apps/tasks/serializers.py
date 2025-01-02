# local imports
from apps.projects.models import Project, ProjectMembership
from apps.projects.serializers import ProjectMembershipSerializer
from apps.tasks.models import Task, TaskAssignment, Comment, StatusChangeRequest
from apps.users.serializers import CustomUserSerializer, DetailedUserSerializer
# django imports
from django.contrib.auth import get_user_model
from django.utils  import timezone
from django.urls import reverse
from django.db import transaction
# third-party imports
from rest_framework import serializers
from rest_framework.generics import ListCreateAPIView
from rest_framework.exceptions import ValidationError
User = get_user_model()

class TaskAssignmentSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for task assignment details.
    """
    user = serializers.CharField(source='user.username')
    membership_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskAssignment
        fields = ['id', 'user', 'assigned_at', 'membership_url']

    def get_membership_url(self, obj):
        """
        Retrieve the membership URL from the ProjectMembershipSerializer.
        """
        request = self.context.get('request')
        if not request:
            print("Request not found in context.")  # Debugging
            return None

        # Directly get the URL for the membership if available
        membership_url = None
        try:
            membership = ProjectMembership.objects.get(
                project=obj.task.project,
                user=obj.user
            )
            membership_url = request.build_absolute_uri(reverse(
                'project-membership-detail', kwargs={'id': membership.id}
            ))
        except ProjectMembership.DoesNotExist:
            print("ProjectMembership does not exist.")  # Debugging

        return membership_url



class TaskListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing tasks with minimal information.
    """
    class Meta:
        model = Task
        fields = ['id', 'name', 'due_date', 'status']
        
class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for showing detailed information about a task.
    """
    assignments_ = TaskAssignmentSerializer(source='assignments', many=True, read_only=True)
    project = serializers.StringRelatedField()  # Show project name or use ProjectSerializer if details are needed
    assigned_by = serializers.StringRelatedField()  # Display the username of the assigned_by user
    approved_by = serializers.StringRelatedField()  # Display the username of the approved_by user

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'status', 'due_date', 'project',
            'created_at', 'updated_at', 'total_assignees', 'need_approval',
            'assigned_by', 'approved_by', 'assignments_'
        ]
        read_only_fields = ['id', 'approved_by', 'assigned_by']


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new task with optional assignees.
    """
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    assigned_by = serializers.HiddenField(default=serializers.CurrentUserDefault())  # Automatically assign the user creating the task
    assignees = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, required=False)  # List of assignees for the task
    due_date = serializers.DateTimeField(required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'status', 'due_date', 'total_assignees',
            'project', 'need_approval', 'assigned_by', 'assignees', 'approved_by'
        ]
        read_only_fields = ['id', 'assigned_by', 'total_assignees', 'approved_by']

    def validate_due_date(self, value):
        if value and value.date() < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value

    def validate_assignees(self, value):
        project_id = self.initial_data.get('project')
        if not project_id:
            raise serializers.ValidationError("Project is required.")
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project does not exist.")

        # Check membership directly through ProjectMembership model
        project_members = project.memberships.values_list('user', flat=True)
        for assignee in value:
            if assignee.id not in project_members:
                raise serializers.ValidationError(f"User {assignee} is not a member of the project.")
        return value



    def create(self, validated_data):
        """
        Create a new task, assign members (including project owner if not already in assignees), and update total_assignees.
        """
        assignees = validated_data.pop('assignees', [])
        task = Task.objects.create(**validated_data)

        # Handle task assignments
        for user in assignees:
            TaskAssignment.objects.create(task=task, user=user)

        # Update total_assignees count
        task.total_assignees = len(assignees)
        task.save()
        return task

    def to_representation(self, instance):
        """
        Customize the response to show assignees and total_assignees.
        """
        return {
            'id': instance.id,
            'name': instance.name,
            'description': instance.description,
            'status': instance.status,
            'due_date': instance.due_date,
            'project': instance.project.name,  # Assuming you have a 'name' field in the Project model
            'total_assignees': instance.total_assignees,
            'assigned_by': instance.assigned_by.username,
            'assignees': TaskAssignmentSerializer(
                instance.assignments.all(), 
                many=True,
                context=self.context
            ).data,
        }
    
class TaskUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating task details, including managing assignees.
    """
    assignees = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, required=False)  # Assignees list
    
    class Meta:
        model = Task
        fields = [
            'name', 'description', 'status', 'due_date', 'project', 
            'need_approval', 'assignees', 'assigned_by', 'approved_by', 'total_assignees'
        ]
        read_only_fields = ['assigned_by', 'total_assignees', 'project']  # Prevent users from modifying these fields
        
    def validate_due_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value
    
    def update(self, instance, validated_data):
        """
        Partially update task fields and manage assignees with optimized database queries.
        """
        assignees = validated_data.pop('assignees', None)
        new_assignees = []
        removed_assignees = []
        # Update task fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # If assignees are provided, handle member management
        if assignees is not None:
            # Get the current assignees (users already assigned to the task)
            current_assignees = set(instance.assignments.values_list('user', flat=True))
            new_assignees_set = set(assignee.id for assignee in assignees)


            to_remove = current_assignees - new_assignees_set
            to_add = new_assignees_set - current_assignees
            
            if to_remove:
                # Remove assignees
                TaskAssignment.objects.filter(task=instance, user__in=to_remove).delete()
                to_remove = list(to_remove)
                
            if to_add:
                for user_id in to_add:
                    TaskAssignment.objects.create(task=instance, user_id=user_id)
                to_add = list(to_add)
            

            # Update total_assignees count
            instance.total_assignees = len(assignees)

            # Save the task instance
            instance.save()

            self.context['new_assignees'] = User.objects.filter(id__in=to_add)
            self.context['removed_assignees'] = User.objects.filter(id__in=to_remove)
            
        return instance

    def destroy(self, instance):
        """
        Delete the task and its associated assignments.
        """
        # Remove all task assignments before deleting the task
        TaskAssignment.objects.filter(task=instance).delete()
        instance.delete()

        return instance
    
    def to_representation(self, instance):
        return TaskDetailSerializer(instance, context=self.context).data
    
# Task status change by assignee
class TaskStatusChangeSerializer(serializers.ModelSerializer):
    """
    Serializer to handle the task status update. This serializer only validates 
    the status change for tasks that do not require approval.
    """
    class Meta:
        model = Task
        fields = ['status']

    def validate_status(self, value):
        """
        Validates the status input to ensure it is a valid task status.
        """
        valid_statuses = ['completed']
        if value not in valid_statuses:
            raise serializers.ValidationError("Invalid status value.")
        return value
#==================#
# Comment Features #
#==================#

class CommentListSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    task = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'content', 'created_at', 'updated_at', 'parent', 'reply_count', 'mention_count']
        read_only_fields = ['author', 'created_at', 'updated_at', 'reply_count', 'mention_count']

    def get_task(self, obj):
        return {'id': obj.task.id, 'name': obj.task.name}

class CommentDetailSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    mentioned_users = CustomUserSerializer(many=True, read_only=True)
    task = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'task', 'project', 'author', 'content', 'created_at', 'updated_at', 'mentioned_users', 'parent', 'reply_count', 'mention_count', 'replies']
        read_only_fields = ['author', 'created_at', 'updated_at', 'mentioned_users', 'reply_count', 'mention_count', 'replies']

    def get_task(self, obj):
        return {'id': obj.task.id, 'name': obj.task.name}

    def get_project(self, obj):
        return {'id': obj.task.project.id, 'name': obj.task.project.name}

    def get_replies(self, obj):
        if obj.parent is None:  # Only get replies for top-level comments
            replies = Comment.objects.filter(parent=obj).select_related('author').prefetch_related('mentioned_users')
            return CommentListSerializer(replies, many=True, context=self.context).data
        return []

class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'task', 'content', 'parent']
        read_only_fields = ['id']

    def validate(self, attrs):
        user = self.context['request'].user
        task = attrs.get('task')

        if not task:
            raise serializers.ValidationError("Task is required.")

        if not task.assignments.filter(user=user).exists():
            raise serializers.ValidationError("You are not assigned to this task.")
        
        content = attrs.get('content')
        if len(content) > 1000:
            raise serializers.ValidationError("Content must not exceed 1000 characters.")
        
        parent = attrs.get('parent')
        if parent:
            if parent.task != task:
                raise serializers.ValidationError("Parent comment must belong to the same task.")
            if parent.parent:
                raise serializers.ValidationError("Cannot reply to a reply. Only top-level comments can have replies.")
        
        return attrs

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
    
#=========================#
# Status Changes Requests #
#=========================#
class StatusChangeRequestSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = StatusChangeRequest
        fields = ['id', 'task', 'task_name', 'user', 'username', 'request_time', 'reason', 'status', 'approved_by']
        read_only_fields = ['status', 'approved_by', 'user']

    def validate(self, data):
        task = data.get('task')
        if task.status not in ['in_progress', 'overdue', 'not_started']:
            raise serializers.ValidationError("Only tasks that are 'in_progress' or 'overdue' can be marked as completed.")
        
        if not task.need_approval:
            raise serializers.ValidationError("Task doesn't require approval to be completed.")
        
        return data

    def update(self, instance, validated_data):
        """
        Override the update method to handle the accept/reject action.
        This method is now only used for regular updates (other than accept/reject).
        """
        status = instance.status
        if status != 'pending':
            raise serializers.ValidationError("Only pending status change requests can be updated.")
        return super().update(instance, validated_data)

class StatusChangeActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject"])
