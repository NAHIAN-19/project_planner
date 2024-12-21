from django.db import models
from apps.projects.models import Project
from django.contrib.auth import get_user_model
User = get_user_model()
class Task(models.Model):
    STATUS_CHOICES = (
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("overdue", "Overdue"),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="not_started"
    )
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks_creator")
    need_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tasks_approver", null=True, blank=True
    )
    class Meta:
        db_table = "tasks"
        ordering = ["-due_date", "status"]

    def __str__(self):
        return self.name


class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="task_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "task_assignments"
        unique_together = ("task", "user")

    def __str__(self):
        return f"{self.user.username} assigned to {self.task.name}"




