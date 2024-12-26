from rest_framework.permissions import BasePermission
from apps.projects.models import Project
from apps.tasks.models import Task
from django.shortcuts import get_object_or_404

class IsTaskAssigneeOrProjectMember(BasePermission):
    def has_permission(self, request, view):
        task_id = request.query_params.get('task_id')
        project_id = request.query_params.get('project_id')

        if task_id:
            task = get_object_or_404(Task, id=task_id)
            return task.assignments.filter(user=request.user).exists()
        elif project_id:
            project = get_object_or_404(Project, id=project_id)
            return project.memberships.filter(user=request.user).exists()
        
        return True  # For user's own comments

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            obj.author == request.user or
            obj.task.assignments.filter(user=request.user).exists()
        )