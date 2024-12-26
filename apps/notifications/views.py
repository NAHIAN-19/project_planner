from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.serializers import NotificationSerializer, NotificationPreferenceSerializer
from core.services.notification_service import notify_user

@extend_schema(tags=['Notifications'])
class NotificationListCreateView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating notifications.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """Filter notifications for the current user only"""
        return Notification.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        """Create notification and trigger real-time notification"""
        notification = serializer.save(recipient=self.request.user)
        notify_user(
            user_id=notification.recipient.id,
            message=notification.message,
            notification_type=notification.notification_type,
            object_id=notification.object_id,
            content_type=notification.content_type
        )

    @extend_schema(
        summary="List Notifications",
        parameters=[
            OpenApiParameter(
                name='page_size',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Number of results per page',
                default=10
            ),
            OpenApiParameter(
                name='is_read',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter by read status'
            ),
        ],
        responses={
            200: inline_serializer(
                name='NotificationListResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField(),
                    'data': NotificationSerializer(many=True)
                }
            )
        }
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'message': 'Notifications retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create Notification",
        request=NotificationSerializer,
        responses={
            201: inline_serializer(
                name='NotificationCreateResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField(),
                    'data': NotificationSerializer()
                }
            )
        },
        examples=[
            OpenApiExample(
                'Project Update',
                value={
                    'message': 'Project deadline updated',
                    'notification_type': 'project',
                    'object_id': 1,
                    'content_type': 'project'
                }
            ),
            OpenApiExample(
                'Task Assignment',
                value={
                    'message': 'New task assigned to you',
                    'notification_type': 'task',
                    'object_id': 5,
                    'content_type': 'task'
                }
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'status': 'success',
            'message': 'Notification created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

@extend_schema(tags=['Notifications'])
class NotificationRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating and deleting individual notifications.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """Ensure users can only access their own notifications"""
        return Notification.objects.filter(recipient=self.request.user)

    @extend_schema(
        summary="Get Single Notification",
        responses={
            200: inline_serializer(
                name='NotificationDetailResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField(),
                    'data': NotificationSerializer()
                }
            )
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'message': 'Notification retrieved successfully',
            'data': serializer.data
        })

    @extend_schema(
        summary="Update Notification",
        request=NotificationSerializer,
        responses={
            200: inline_serializer(
                name='NotificationUpdateResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField(),
                    'data': NotificationSerializer()
                }
            )
        }
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'status': 'success',
            'message': 'Notification updated successfully',
            'data': serializer.data
        })

    @extend_schema(
        summary="Delete Notification",
        responses={
            200: inline_serializer(
                name='NotificationDeleteResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField()
                }
            )
        }
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'status': 'success',
            'message': 'Notification deleted successfully'
        }, status=status.HTTP_200_OK)

@extend_schema(tags=['Notification Preferences'])
class NotificationPreferenceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for managing notification preferences.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer

    def get_queryset(self):
        """Ensure users can only access their own preferences"""
        return NotificationPreference.objects.filter(user=self.request.user)

    @extend_schema(
        summary="Get Notification Preferences",
        responses={
            200: inline_serializer(
                name='PreferenceDetailResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField(),
                    'data': NotificationPreferenceSerializer()
                }
            )
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'message': 'Notification preferences retrieved successfully',
            'data': serializer.data
        })

    @extend_schema(
        summary="Update Notification Preferences",
        request=NotificationPreferenceSerializer,
        responses={
            200: inline_serializer(
                name='PreferenceUpdateResponse',
                fields={
                    'status': serializers.CharField(),
                    'message': serializers.CharField(),
                    'data': NotificationPreferenceSerializer()
                }
            )
        },
        examples=[
            OpenApiExample(
                'Update Preferences',
                value={
                    'task': True,
                    'project': True,
                    'comment': False
                }
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'status': 'success',
            'message': 'Notification preferences updated successfully',
            'data': serializer.data
        })
