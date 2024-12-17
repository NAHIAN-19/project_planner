# from django.contrib.auth.models import User
# from django.db import models
# from project_planner import settings
# from users.models import User
# class Notification(models.Model):
#     recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
#     sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_notifications")
#     message = models.TextField()
#     is_read = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     url = models.URLField(blank=True, null=True)  # Link to the related task, project, etc.

#     def __str__(self):
#         return f"Notification for {self.recipient.username}: {self.message}"

# class NotificationPreference(models.Model):
#     NOTIFICATION_TYPES = [
#         ("project", "Project Notifications"),
#         ("task", "Task Notifications"),
#         ("comment", "Comment Mentions"),
#         ("subscription", "Subscription Updates"),
#     ]

#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")
#     preferences = models.JSONField(default=dict)  # e.g., {"project": True, "task": True, "comment": False}

#     def set_preference(self, notification_type, enabled):
#         self.preferences[notification_type] = enabled
#         self.save()

#     def get_preference(self, notification_type):
#         return self.preferences.get(notification_type, True)  # Default to True if not set

#     def __str__(self):
#         return f"Notification Preferences for {self.user.username}"
