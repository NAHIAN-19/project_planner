# core/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.projects.models import ProjectMembership
from apps.tasks.models import Task, Comment, TaskAssignment, StatusChangeRequest
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
        
        
# update user profile project count on membership creation
@receiver(post_save, sender=ProjectMembership)
def update_user_profile_project_count(sender, instance, created, **kwargs):
    if created:
        instance.user.profile.participated_projects_count += 1
        instance.user.profile.save()
        
@receiver(post_save, sender=Task)
def update_project_and_membership_on_task_save(sender, instance, created, **kwargs):
    """
    Signal to update the total task counts and completed task counts for the project
    and related memberships when a task is created or updated.
    """
    project = instance.project

    # Only update project total tasks if there was an actual change
    if created or instance.project.total_tasks != project.tasks.count():
        project.total_tasks = project.tasks.count()
        project.save()

    # Update total tasks and completed tasks for each membership in the project
    memberships = ProjectMembership.objects.filter(project=project)

    for membership in memberships:
        # Update task counts only if necessary (e.g., if assignments exist or status changed)
        membership.update_task_counts()


@receiver(post_save, sender=TaskAssignment)
@receiver(post_delete, sender=TaskAssignment)
def update_membership_on_task_assignment_change(sender, instance, **kwargs):
    """
    Signal to update task counts in project memberships when a task assignment is created or deleted.
    """
    project = instance.task.project
    user = instance.user

    # Only update the membership if the task assignment or deletion affects task counts
    membership = ProjectMembership.objects.filter(project=project, user=user).first()
    if membership:
        membership.update_task_counts()


@receiver(post_save, sender=Task)
def update_membership_on_task_status_change(sender, instance, **kwargs):
    """
    Signal to update completed task counts when a task's status changes to 'completed'.
    """
    if instance.status == 'completed':
        project = instance.project

        # Update completed tasks for all memberships associated with this task
        for assignment in instance.assignments.all():
            membership = ProjectMembership.objects.filter(
                project=project, user=assignment.user
            ).first()
            if membership:
                membership.update_task_counts()