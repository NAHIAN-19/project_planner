from django.db import models
from apps.users.models import User, UserMetadata

class Project(models.Model):
    STATUS_CHOICES = (
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="not_started"
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_projects")
    members = models.ManyToManyField(User, related_name="projects", through="ProjectMembership")

    class Meta:
        db_table = "projects"
        
    def __str__(self):
        return self.name



class ProjectMembership(models.Model):
    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("member", "Member"),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    
    # Foreign key to UserMetaData for denormalized user information
    user_metadata = models.ForeignKey(UserMetadata, on_delete=models.CASCADE, related_name="project_memberships")

    class Meta:
        db_table = "project_memberships"
        unique_together = ("project", "user")
        
    def __str__(self):
        return f"{self.user.username} ({self.role}) in {self.project.name}"



