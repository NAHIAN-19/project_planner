from django.db import models
from django.utils.timezone import now
from django.contrib.auth import get_user_model

User = get_user_model()


class Project(models.Model):
    """
    Represents a project with members and tasks.
    Tracks the total number of tasks, project status, and member count.
    """
    PROJECT_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]

    # Core fields
    name = models.CharField(max_length=255)  # Name of the project
    description = models.TextField(blank=True, null=True)  # Optional description
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_projects'
    )  # Owner of the project
    created_at = models.DateTimeField(auto_now_add=True)  # Project creation timestamp

    # Tracking fields
    total_tasks = models.PositiveIntegerField(default=0)  # Total tasks associated with the project
    status = models.CharField(
        max_length=20, 
        choices=PROJECT_STATUS_CHOICES, 
        default='not_started'
    )  # Current status of the project
    due_date = models.DateTimeField(null=True, blank=True)  # Optional due date for the project
    total_member_count = models.PositiveIntegerField(default=1)  # Total members in the project (including the owner)

    def __str__(self):
        return self.name

    def update_task_counts(self):
        """
        Updates the total number of tasks in the project by counting associated tasks.
        This should be called whenever tasks are added or removed.
        """
        self.total_tasks = self.tasks.count()
        self.save()

    def update_member_count(self):
        """
        Updates the total number of members in the project by counting the memberships.
        This should be called whenever members are added or removed.
        """
        self.total_member_count = self.memberships.count()
        self.save()


class ProjectMembershipQuerySet(models.QuerySet):
    """
    Custom QuerySet for ProjectMembership to optimize data fetching.
    """

    def with_related_data(self):
        """
        Optimizes fetching of related project and user data using select_related.
        Use this when you need to access related fields frequently.
        """
        return self.select_related('project', 'user')


class ProjectMembershipManager(models.Manager):
    """
    Custom Manager for ProjectMembership to provide optimized queries.
    """

    def get_queryset(self):
        """
        Overrides the default queryset to include the custom QuerySet.
        """
        return ProjectMembershipQuerySet(self.model, using=self._db)

    def with_related_data(self):
        """
        Provides an entry point to use the optimized QuerySet.
        """
        return self.get_queryset().with_related_data()


class ProjectMembership(models.Model):
    """
    Represents the membership of a user in a project.
    Tracks the user's tasks and completion statistics within the project.
    """
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='memberships'
    )  # The project this membership is associated with
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='project_memberships'
    )  # The user who is a member of the project
    joined_at = models.DateTimeField(default=now)  # Timestamp of when the user joined the project

    # Task tracking fields
    total_tasks = models.PositiveIntegerField(default=0)  # Total tasks assigned to the user in this project
    completed_tasks = models.PositiveIntegerField(default=0)  # Total tasks completed by the user in this project

    # Custom manager
    objects = ProjectMembershipManager()

    class Meta:
        unique_together = ('project', 'user')  # Ensures a user cannot have duplicate memberships in a project

    def __str__(self):
        return f"{self.user.username} in {self.project.name}"

    def update_task_counts(self):
        """
        Updates the total and completed tasks for this user in the project.
        This should be called whenever tasks are assigned or their status changes.
        """
        self.total_tasks = self.project.tasks.filter(taskassignments__user=self.user).count()
        self.completed_tasks = self.project.tasks.filter(
            taskassignments__user=self.user, 
            status='completed'
        ).count()
        self.save()
