from typing import Any

# Local imports
from apps.projects.models import Project
from apps.tasks.models import (
    Task, TaskAssignment, Comment, StatusChangeRequest
)
from apps.tasks.serializers import (
    TaskCreateSerializer, TaskSerializer, TaskUpdateSerializer, StatusChangeRequestSerializer,
    CommentCreateSerializer, CommentListSerializer, CommentDetailSerializer, TaskStatusChangeSerializer
)
from apps.tasks.permissions import IsTaskAssigneeOrProjectMember, IsProjectOwnerOrReadOnly

# Django imports
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

# Third-party imports
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample, OpenApiTypes
)
from rest_framework import status, filters, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from rest_framework.serializers import Serializer

# Utility for standardized responses
def standardized_response(
    status_code: int,
    status_message: str,
    message: str,
    data: dict | None = None
) -> Response:
    """
    Utility to create standardized API responses.
    """
    response = {
        "status": status_message,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    return Response(response, status=status_code)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

#=================#
# Task Views      #
#=================#

class TaskListCreateView(ListCreateAPIView):
    """
    View to list all tasks or create a new task with assignees.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    pagination_class = StandardResultsSetPagination
    queryset = Task.objects.all()
    serializer_class = TaskCreateSerializer  # Use TaskCreateSerializer for creation

    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filterset_fields = ['status', 'due_date', 'assigned_by', 'project', 'need_approval']  # Fields to filter by
    search_fields = ['name', 'description']  # Fields to search within (full-text search)
    ordering_fields = ['due_date', 'status', 'created_at']  # Allow ordering by these fields
    ordering = ['-due_date']  # Default ordering by due_date descending

    def get_serializer_class(self):
        """
        Override to return the appropriate serializer class based on the request method.
        """
        if self.request.method == 'GET':
            return TaskSerializer  # Use TaskSerializer for GET requests (task details view)
        return TaskCreateSerializer  # Use TaskCreateSerializer for POST requests (task creation)

    @extend_schema(
        summary="List and Create Tasks",
        description="Retrieve a list of tasks with filters or create a new task.",
        parameters=[
            OpenApiParameter(name='status', description='Filter tasks by status', required=False, type=str),
            OpenApiParameter(name='due_date', description='Filter tasks by due date', required=False, type=str),
            OpenApiParameter(name='assigned_by', description='Filter tasks by assigner ID', required=False, type=int),
            OpenApiParameter(name='project', description='Filter tasks by project ID', required=False, type=int),
            OpenApiParameter(name='need_approval', description='Filter tasks requiring approval', required=False, type=bool),
            OpenApiParameter(name='page', description='Page number for pagination', required=False, type=int),
            OpenApiParameter(name='page_size', description='Number of items per page', required=False, type=int),
        ],
        request=TaskCreateSerializer,
        responses={
            200: TaskSerializer(many=True),
            201: TaskSerializer,
            400: OpenApiExample(
                'Validation Error',
                value={"detail": "Invalid input."},
                response_only=True,
            ),
            403: OpenApiExample(
                'Forbidden',
                value={"detail": "You do not have permission to perform this action."},
                response_only=True,
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class TaskRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete a specific task.
    """
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    serializer_class = TaskUpdateSerializer

    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ['status', 'due_date', 'assigned_by', 'project']  # Fields to filter by
    ordering_fields = ['due_date', 'status', 'created_at']  # Allow ordering by these fields
    ordering = ['-due_date']  # Default ordering by due_date descending

    def get_serializer_class(self):
        """
        Use a different serializer for GET request to exclude certain fields.
        """
        if self.request.method == 'GET':
            return TaskSerializer
        return TaskUpdateSerializer

    def get_queryset(self):
        """
        Return the task details with assignments, project, and owner info.
        Optimize the query by using select_related and prefetch_related.
        """
        queryset = Task.objects.select_related(
            'project',                     # Use select_related for the project field (foreign key)
            'project__owner'               # Use select_related for the project's owner (foreign key)
        ).prefetch_related(
            'assignments__user'            # Use prefetch_related for many-to-many relationships (task assignments)
        )

        # Apply additional filtering to the queryset if needed
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @extend_schema(
        summary="Retrieve, Update or Delete Task",
        description="Retrieve task details, update them, or delete the task.",
        responses={
            200: TaskSerializer,
            204: None,
            403: OpenApiExample(
                'Forbidden',
                value={"detail": "You do not have permission to perform this action."},
                response_only=True,
            ),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Partially Update Task",
        description="Partially update task details.",
        request=TaskUpdateSerializer,
        responses={
            200: TaskSerializer,
            400: OpenApiExample(
                'Validation Error',
                value={"detail": "Invalid input."},
                response_only=True,
            ),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete Task",
        description="Delete a specific task.",
        responses={
            204: None,
            403: OpenApiExample(
                'Forbidden',
                value={"detail": "You do not have permission to perform this action."},
                response_only=True,
            ),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def perform_update(self, serializer):
        """
        Ensure that only the project owner can update the task.
        """
        task = serializer.instance
        if self.request.user != task.project.owner:
            raise PermissionDenied("Only the project owner can update this task.")
        serializer.save()

    def perform_destroy(self, instance):
        """
        Delete the task and its associated task assignments.
        """
        TaskAssignment.objects.filter(task=instance).delete()  # Delete all task assignments first
        instance.delete()  # Now delete the task
        
class TaskStatusChangeView(APIView):
    """
    API view for updating the task status without requiring approval.
    This view allows users to directly update the task status if the task 
    does not require approval and if the user is part of the task.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update Task Status",
        description="Update the status of a task if the user is assigned and the task does not require approval.",
        request=TaskStatusChangeSerializer,
        responses={
            200: OpenApiExample(
                'Success',
                value={"detail": "Task status updated successfully."},
                response_only=True,
            ),
            403: OpenApiExample(
                'Forbidden',
                value={"detail": "You must be assigned to the task to change its status."},
                response_only=True,
            ),
            404: OpenApiExample(
                'Not Found',
                value={"detail": "Task not found."},
                response_only=True,
            ),
            400: OpenApiExample(
                'Validation Error',
                value={"status": ["Invalid status value."]},
                response_only=True,
            ),
        },
    )
    def patch(self, request, pk):
        """
        Handles PATCH requests to update a task's status.

        Arguments:
            pk: The primary key of the task to be updated.

        Returns:
            Response with status code 200 for successful updates or 400 for failed validation.
        """
        try:
            task = Task.objects.get(id=pk)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

        if task.need_approval:
            raise PermissionDenied("Task requires approval to change status.")
        
        if not TaskAssignment.objects.filter(task=task, user=request.user).exists():
            raise PermissionDenied("You must be assigned to the task to change its status.")

        serializer = TaskStatusChangeSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Task status updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentListCreateView(ListCreateAPIView):
    """
    View to list and create comments for tasks.
    """
    permission_classes = [IsAuthenticated, IsTaskAssigneeOrProjectMember]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'author']
    ordering_fields = ['created_at', 'updated_at']
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        """
        Retrieve comments with filters and optimized queries.
        """
        queryset = Comment.objects.select_related('author', 'task', 'task__project')

        task_id = self.request.query_params.get('task_id')
        project_id = self.request.query_params.get('project_id')
        user_id = self.request.query_params.get('user_id')
        parent_id = self.request.query_params.get('parent_id')

        if task_id:
            queryset = queryset.filter(task_id=task_id)
        elif project_id:
            queryset = queryset.filter(task__project_id=project_id)
        elif user_id:
            queryset = queryset.filter(author_id=user_id)
        else:
            queryset = queryset.filter(author=self.request.user)

        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        else:
            queryset = queryset.filter(parent=None)  # Only top-level comments

        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentListSerializer

    @extend_schema(
        summary="List and Create Comments",
        description="Get a list of comments based on query parameters or create a new comment.",
        parameters=[
            OpenApiParameter(name='task_id', description='ID of the task', required=False, type=int),
            OpenApiParameter(name='project_id', description='ID of the project', required=False, type=int),
            OpenApiParameter(name='user_id', description='ID of the user', required=False, type=int),
            OpenApiParameter(name='parent_id', description='ID of the parent comment for replies', required=False, type=int),
            OpenApiParameter(name='page', description='Page number for pagination', required=False, type=int),
            OpenApiParameter(name='page_size', description='Number of items per page', required=False, type=int),
        ],
        responses={
            200: CommentListSerializer(many=True),
            201: CommentListSerializer,
            403: OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
            ),
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class CommentDetailView(RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete a specific comment.
    """
    queryset = Comment.objects.select_related('author', 'task', 'task__project').prefetch_related('mentioned_users')
    serializer_class = CommentDetailSerializer
    permission_classes = [IsAuthenticated, IsTaskAssigneeOrProjectMember]
    throttle_classes = [UserRateThrottle]

    @extend_schema(
        summary="Retrieve, Update or Delete a Comment",
        description="Get details of a specific comment, update its content, or delete it.",
        responses={
            200: CommentDetailSerializer,
            204: None,
            403: OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
            ),
        }
    )
    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Handle GET request to retrieve comment details.
        """
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a Comment",
        description="Update the content of a specific comment.",
        responses={
            200: CommentDetailSerializer,
            403: OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
            ),
        }
    )
    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Handle PUT request to update the comment.
        """
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a Comment",
        description="Delete a specific comment.",
        responses={
            204: None,
            403: OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
            ),
        }
    )
    def delete(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Handle DELETE request to delete the comment.
        """
        return super().delete(request, *args, **kwargs)

class StatusChangeRequestListCreateView(ListCreateAPIView):
    """
    API view for listing and creating status change requests.
    """
    queryset = StatusChangeRequest.objects.all()
    serializer_class = StatusChangeRequestSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [UserRateThrottle]

    @extend_schema(
        summary="List Status Change Requests",
        description="Retrieve a paginated list of status change requests. Optionally filter by task or project ID.",
        parameters=[
            OpenApiParameter("task_id", OpenApiTypes.INT, description="Filter requests by Task ID"),
            OpenApiParameter("project_id", OpenApiTypes.INT, description="Filter requests by Project ID"),
        ],
        responses={
            200: StatusChangeRequestSerializer(many=True),
            404: OpenApiExample(
                "Not Found",
                value={"detail": "Task/Project not found."},
                response_only=True,
            ),
        }
    )
    def get_queryset(self):
        """
        Optionally filter status change requests by task or project.
        """
        queryset = StatusChangeRequest.objects.all()
        task_id = self.request.query_params.get('task_id')
        project_id = self.request.query_params.get('project_id')

        if task_id:
            try:
                task = Task.objects.get(id=task_id)
            except Task.DoesNotExist:
                raise NotFound(detail="Task not found.")

            # Check if the user is assigned to the task
            if not task.assignments.filter(user=self.request.user).exists():
                raise PermissionDenied(detail="You are not assigned to this task.")

            queryset = queryset.filter(task_id=task_id)

        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                raise NotFound(detail="Project not found.")

            # Check if the user is part of the project
            if not project.memberships.filter(user=self.request.user).exists() and project.owner != self.request.user:
                raise PermissionDenied(detail="You are not a member of this project or the owner.")

            tasks = project.tasks.all()
            queryset = queryset.filter(task__in=tasks)

        return queryset

    @extend_schema(
        summary="Create Status Change Request",
        description="Create a new status change request for a task.",
        request=StatusChangeRequestSerializer,
        responses={
            201: StatusChangeRequestSerializer,
            400: OpenApiExample(
                "Validation Error",
                value={"detail": "Invalid data."},
                response_only=True,
            ),
        }
    )
    def perform_create(self, serializer):
        """
        Automatically set the user making the request as the creator.
        """
        serializer.save(user=self.request.user)


class StatusChangeRequestRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, or deleting a specific status change request.
    """
    queryset = StatusChangeRequest.objects.all()
    serializer_class = StatusChangeRequestSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrReadOnly]

    @extend_schema(
        summary="Retrieve Status Change Request",
        description="Retrieve details of a specific status change request by its ID.",
        responses={
            200: StatusChangeRequestSerializer,
            404: OpenApiExample(
                "Not Found",
                value={"detail": "Status change request not found."},
                response_only=True,
            ),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update Status Change Request",
        description="Update details of a status change request (excluding approval/rejection logic).",
        request=StatusChangeRequestSerializer,
        responses={
            200: StatusChangeRequestSerializer,
            400: OpenApiExample(
                "Validation Error",
                value={"detail": "Invalid data."},
                response_only=True,
            ),
        }
    )
    def perform_update(self, serializer):
        super().perform_update(serializer)

    @extend_schema(
        summary="Delete Status Change Request",
        description="Delete a specific status change request.",
        responses={
            204: None,
            404: OpenApiExample(
                "Not Found",
                value={"detail": "Status change request not found."},
                response_only=True,
            ),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class StatusChangeRequestAcceptRejectView(APIView):
    """
    API view for accepting or rejecting a status change request.
    """
    permission_classes = [IsAuthenticated, IsProjectOwnerOrReadOnly]

    @extend_schema(
        summary="Accept/Reject Status Change Request",
        description=(
            "Approve or reject a pending status change request by specifying the action ('accept' or 'reject'). "
            "Automatically updates the task status if accepted."
        ),
        request=OpenApiParameter(
            "action",
            OpenApiTypes.STR,
            enum=["accept", "reject"],
            description="Action to perform ('accept' or 'reject').",
        ),
        responses={
            200: StatusChangeRequestSerializer,
            400: OpenApiExample(
                "Invalid Action",
                value={"detail": "Invalid action. Must be 'accept' or 'reject'."},
                response_only=True,
            ),
            404: OpenApiExample(
                "Not Found",
                value={"detail": "Status change request not found."},
                response_only=True,
            ),
        }
    )
    def post(self, request, pk):
        try:
            # Retrieve the status change request by ID
            status_change_request = StatusChangeRequest.objects.get(id=pk)
        except StatusChangeRequest.DoesNotExist:
            raise NotFound(detail="Status change request not found.")

        # Get the action (accept or reject)
        action = request.data.get('action')

        if action not in ['accept', 'reject']:
            return Response({"detail": "Invalid action. Must be 'accept' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        if status_change_request.status != 'pending':
            return Response({"detail": "This status change request is not pending."}, status=status.HTTP_400_BAD_REQUEST)

        # Perform the accept or reject action
        if action == 'accept':
            # Mark the request as approved and update the task's status
            status_change_request.status = 'approved'
            status_change_request.task.status = 'completed'
            status_change_request.approved_by = request.user
            status_change_request.task.save()
        elif action == 'reject':
            # Mark the request as rejected
            status_change_request.status = 'rejected'

        # Save the status change request after the action
        status_change_request.save()

        # Serialize and return the updated status change request
        serializer = StatusChangeRequestSerializer(status_change_request)
        return Response(serializer.data, status=status.HTTP_200_OK)