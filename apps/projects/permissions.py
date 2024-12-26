from rest_framework import permissions

class IsProjectOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only project owners to modify tasks.
    """
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or obj.project.owner == request.user