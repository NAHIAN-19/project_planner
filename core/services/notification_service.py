from django.dispatch import receiver
from apps.notifications.models import Notification, NotificationPreference
from core.tasks import send_notification
from django.contrib.auth import get_user_model
User = get_user_model()
def notify_user(user_id, message, notification_type, content_type=None, object_id=None):
    user = User.objects.get(id=user_id)
    user_preferences = NotificationPreference.objects.get(user=user)
    if not user_preferences.get_preference(notification_type):
        return

    notification = Notification.objects.create(
        recipient=user,
        message=message,
        notification_type=notification_type,
        content_type=content_type,
        object_id=object_id
    )

    send_notification.delay(
        user_id, 
        {
            "id": notification.id,
            "message": message,
            "type": notification_type,
            "created_at": str(notification.created_at)
        }
    )
