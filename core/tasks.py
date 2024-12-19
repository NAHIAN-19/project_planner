# core/tasks.py
from celery import shared_task
from apps.users.models import User
from django.core.mail import send_mail
from django.conf import settings

# Task to create or update user metadata
@shared_task
def create_or_update_user_metadata(sender, instance, created, **kwargs):
    from apps.users.models import UserMetadata
    if created:
        UserMetadata.objects.create(user=instance)  # Create user metadata on user creation
    else:
        instance.metadata.sync_from_user()

# Task to send emails
@shared_task
def send_email(subject, message, recipient):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
    )
