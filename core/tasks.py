# core/tasks.py
from celery import shared_task
from apps.users.models import User
from django.core.mail import send_mail
from django.conf import settings

# Task to create or update user metadata
@shared_task
def create_or_update_user_metadata(user_id, created):
    from apps.users.models import UserMetadata
    user = User.objects.get(id=user_id)
    if created:
        UserMetadata.objects.create(
            user=user,
            username=user.username,
            email=user.email,
        )
    else:
        metadata, _ = UserMetadata.objects.get_or_create(user=user)
        metadata.username = user.username
        metadata.email = user.email
        metadata.save()

# Task to send emails
@shared_task
def send_email(subject, message, recipient):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
    )
