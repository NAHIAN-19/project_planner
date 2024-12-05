from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from users.models import CustomUser
from projects.models import Project

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
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="created_tasks")
    assigned_to = models.ManyToManyField(CustomUser, related_name="assigned_tasks")

    class Meta:
        db_table = "tasks"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="task_comments")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task_comments"


class TaskStatusReport(models.Model):
    STATUS_CHOICES = (
        ("reported", "Reported"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="status_reports")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="status_reports")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    report_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task_status_reports"

