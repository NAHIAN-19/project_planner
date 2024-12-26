from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import F

User = get_user_model()

class Notification(models.Model):
    """
    Model for storing user notifications with generic relations to various content types.
    Supports tracking read status and delivery status.
    """
    # Core fields
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="notifications", 
        db_index=True,
        help_text="User who will receive the notification"
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="sent_notifications",
        help_text="User who triggered the notification"
    )
    message = models.TextField(help_text="Content of the notification")
    
    # Status tracking
    is_read = models.BooleanField(
        default=False, 
        db_index=True,
        help_text="Indicates if the notification has been read"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        db_index=True,
        help_text="Timestamp when notification was created"
    )
    
    # Generic relation fields
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Type of object this notification refers to"
    )
    object_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="ID of the related object"
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Classification fields
    notification_type = models.CharField(
        max_length=50,
        help_text="Category of notification (e.g., task, project)"
    )
    status = models.CharField(
        max_length=20, 
        default='pending',
        help_text="Delivery status of the notification"
    )

    def mark_as_read(self):
        """Marks the notification as read and saves it"""
        self.is_read = True
        self.save()

    def __str__(self):
        """String representation of the notification"""
        return f"Notification for {self.recipient.username}: {self.message}"

class NotificationPreference(models.Model):
    """
    Model for storing user preferences for different types of notifications.
    Uses JSONField to store flexible preference settings.
    """
    NOTIFICATION_TYPES = [
        ("account", "Account Notifications"),
        ("project", "Project Notifications"),
        ("task", "Task Notifications"),
        ("comment", "Comment Mentions"),
        ("subscription", "Subscription Updates"),
    ]

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="notification_preferences",
        help_text="User whose notification preferences these are"
    )
    preferences = models.JSONField(
        default=dict,
        help_text="JSON object storing notification preferences"
    )

    def get_default_preferences(self):
        """Returns the default notification preferences"""
        return {
            "account": True,
            "project": True,
            "task": True,
            "comment": True,
            "subscription": True
        }

    def set_default_preferences(self):
        """Resets preferences to default values"""
        self.preferences = self.get_default_preferences()
        self.save()

    def set_preference(self, notification_type, enabled):
        """
        Sets a specific notification preference
        Args:
            notification_type (str): Type of notification
            enabled (bool): Whether to enable or disable
        """
        if notification_type not in dict(self.NOTIFICATION_TYPES):
            raise ValueError(f"Invalid notification type: {notification_type}")
        self.preferences[notification_type] = enabled
        self.save()

    def get_preference(self, notification_type):
        """
        Gets the current setting for a notification type
        Returns True by default if not set
        """
        return self.preferences.get(notification_type, True)

    def get_all_preferences(self):
        """Returns all notification preferences"""
        return self.preferences

    def __str__(self):
        """String representation of the preference object"""
        return f"Notification Preferences for {self.user.username}"
