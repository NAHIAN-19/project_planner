# core/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.projects.models import ProjectMembership
from apps.notifications.models import NotificationPreference
from core.tasks import update_project_member_count
from django.contrib.auth import get_user_model
User = get_user_model()

# Signal to update membership count when a project membership is created or deleted
@receiver([post_save, post_delete], sender=ProjectMembership)
def handle_project_membership_change(sender, instance, **kwargs):
    """
    Signal to trigger the Celery task when a membership is created or deleted.
    """
    update_project_member_count.delay(instance.project.id)
    
    
@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    if created:
        NotificationPreference.objects.create(user=instance)