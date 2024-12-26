from celery import shared_task
from apps.projects.models import Project
from django.core.mail import send_mail
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
@shared_task
def update_project_member_count(project_id):
    """
    Task to update the total_member_count for a project.
    """
    project = Project.objects.get(id=project_id)
    project.update_member_count()


# Task to send emails
@shared_task
def send_email(subject, message, recipient):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
    )

@shared_task
def send_notification(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{user_id}",
        {
            "type": "send_notification",
            "message": {
                "content": message,
                "timestamp": str(timezone.now()),
                "type": "notification"
            },
        },
    )
