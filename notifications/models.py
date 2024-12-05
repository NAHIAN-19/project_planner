# notifications app
from django.db import models
from django.conf import settings
from users.models import CustomUser
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("task_assigned", "Task Assigned"),
        ("task_status_changed", "Task Status Changed"),
        ("project_updated", "Project Updated"),
        ("payment_received", "Payment Received"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"

