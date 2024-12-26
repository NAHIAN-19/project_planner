from rest_framework import serializers
from apps.projects.models import Project, ProjectMembership
from apps.projects.serializers import CustomUserSerializer
from apps.tasks.models import Task, TaskAssignment, Comment, StatusChangeRequest
from django.contrib.auth import get_user_model
from django.utils  import timezone
from rest_framework.generics import ListCreateAPIView
from django.db import transaction
from rest_framework.exceptions import ValidationError
User = get_user_model()

class TaskAssignmentSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for task assignment details.
    """
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.none())
    username = serializers.CharField(source='user.username')
    class Meta:
        model = TaskAssignment
        fields = ['user','username', 'assigned_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        task = self.context.get('task')
        if task:
            # Use select_related to optimize related lookups
            project_memberships = task.project.memberships.select_related('user')
            self.fields['user'].queryset = User.objects.filter(
                id__in=project_memberships.values_list('user__id', flat=True)
            )

class TaskSerializer(serializers.ModelSerializer):
    assignments = TaskAssignmentSerializer(many=True, read_only=True)  # if we want to see the assignees
    project = serializers.StringRelatedField()  # Show project name or use ProjectSerializer if details are needed
    assigned_by = serializers.CharField(source='assigned_by.username', required=False)  # Show username for assigned_by
    approved_by = serializers.CharField(source='approved_by.username', required=False)  # Show username for approved_by
    # comments = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'status', 'due_date', 'project',
            'created_at', 'updated_at', 'total_assignees', #'comments',
            'need_approval', 'approved_by', 'assigned_by', 'assignments',
        ]
        read_only_fields = ['approved_by', 'assigned_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the task instance from context
        
        # If this is a list view (e.g., TaskListCreateView), do not include assignments and show only ID for assigned_by and approved_by
        if self.context.get('view') and isinstance(self.context['view'], ListCreateAPIView):
            self.fields.pop('assignments')  # Remove assignments from list view
            # self.fields.pop('comments')  # Remove comments from list view
            self.fields['assigned_by'] = serializers.CharField(source='assigned_by.id', required=False)  # Just ID for assigned_by
            self.fields['approved_by'] = serializers.CharField(source='approved_by.id', required=False)  # Just ID for approved_by
        else:
            # For detail views, show usernames
            self.fields['assigned_by'] = serializers.CharField(source='assigned_by.username', required=False)
            self.fields['approved_by'] = serializers.CharField(source='approved_by.username', required=False, allow_null=True)

    # def get_comments(self, obj):
    #     # Only get top-level comments
    #     comments = obj.comments.filter(parent=None)
    #     return CommentSerializer(comments, many=True, context=self.context).data
    
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
            'project', 'need_approval','assigned_by', 'assignees', 'approved_by'
        ]
        read_only_fields = ['id', 'assigned_by', 'total_assignees', 'approved_by']  # Prevent users from manually modifying the assigned_by field

    def validate_due_date(self, value):
        """
        Ensure the due_date is in the future.
        """
        if value and value < timezone.now():
            raise serializers.ValidationError("Due date must be in the future.")
        return value

    def validate_assignees(self, value):
        """
        Ensure that assignees are members of the project.
        """
        project = self.initial_data.get('project')  # Get the project ID from the initial data
        if project:
            project_instance = Project.objects.get(id=project)
            project_members = ProjectMembership.objects.filter(project=project_instance)
            for assignee in value:
                if assignee not in [member.user for member in project_members]:
                    raise serializers.ValidationError(f"User {assignee} is not a member of the project.")
        return value

    def create(self, validated_data):
        """
        Create a new task, assign members (including project owner if not already in assignees), and update total_assignees.
        """
        assignees = validated_data.pop('assignees', [])
        project = validated_data['project']

        # Ensure the project owner is added to the assignees if not already included
        project_owner = project.owner  # Assuming 'owner' is the field for the project owner


        # Create the task
        task = Task.objects.create(**validated_data)

        # Handle task assignments (including the project owner)
        if assignees:
            for user in assignees:
                TaskAssignment.objects.create(task=task, user=user)

            # Update the total_assignees count
            task.total_assignees = len(assignees)
            task.save()
        return task
    
    def to_representation(self, instance):
        """
        Customize the response to show assignees and total_assignees.
        """
        # Standard representation
        representation = super().to_representation(instance)

        # Add the assignees' IDs if they are available
        assignees = instance.assignments.all()
        representation['assignees'] = [assignment.user.id for assignment in assignees]

        # Return the updated representation
        return representation
    
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

    def update(self, instance, validated_data):
        """
        Partially update task fields and manage assignees with optimized database queries.
        """
        assignees = validated_data.pop('assignees', None)

        # Update task fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # If assignees are provided, handle member management
        if assignees is not None:
            # Get the current assignees (users already assigned to the task)
            current_assignees = set(instance.assignments.values_list('user', flat=True))

            # Convert assignees to a set for easy comparison
            assignees_set = set(assignees)

            # Find assignees to be added and removed
            assignees_to_add = assignees_set - current_assignees
            assignees_to_remove = current_assignees - assignees_set

            # Begin a transaction block
            with transaction.atomic():
                # Add new assignees (avoid duplicates)
                add_assignments = [
                    TaskAssignment(task=instance, user=assignee)
                    for assignee in assignees_to_add
                    if not TaskAssignment.objects.filter(task=instance, user=assignee).exists()
                ]
                if add_assignments:
                    TaskAssignment.objects.bulk_create(add_assignments)

                # Remove assignees
                if assignees_to_remove:
                    TaskAssignment.objects.filter(
                        task=instance, user__in=assignees_to_remove
                    ).delete()

                # Update total_assignees count
                instance.total_assignees = len(assignees)

                # Save the task instance
                instance.save()

        return instance

    def destroy(self, instance):
        """
        Delete the task and its associated assignments.
        """
        # Remove all task assignments before deleting the task
        TaskAssignment.objects.filter(task=instance).delete()
        instance.delete()

        return instance
    
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
