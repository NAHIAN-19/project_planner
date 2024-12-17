from django.db import models
from apps.users.models import User, UserMetadata
from apps.projects.models import Project

class Task(models.Model):
    STATUS_CHOICES = (
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="not_started"
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_tasks"
    )
    assigned_to = models.ManyToManyField(
        User, through="TaskAssignment", related_name="assigned_tasks"
    )

    class Meta:
        db_table = "tasks"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="task_assignments")
    user_metadata = models.ForeignKey(
        UserMetadata, on_delete=models.CASCADE, related_name="task_assignments"
    )

    class Meta:
        db_table = "task_assignments"
        unique_together = ("task", "user")

    def __str__(self):
        return f"{self.user.username} assigned to {self.task.name}"




