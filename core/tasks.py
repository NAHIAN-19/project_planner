# core/tasks.py
from celery import shared_task
from apps.projects.models import Project
from django.core.mail import send_mail
from django.conf import settings

    
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
