from rest_framework import permissions


class IsProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow the owner of a project to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # If the method is a safe method, allow access
        if request.method in permissions.SAFE_METHODS:
            return True
        # Allow only the owner of the project to edit it
        return obj.owner == request.user