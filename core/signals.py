# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.users.models import User, UserMetadata
from core.tasks import create_or_update_user_metadata

# Signal to create or update user metadata when a user is created/modified
@receiver(post_save, sender=User)
def create_or_update_user_metadata_signal(sender, instance, created, **kwargs):
    create_or_update_user_metadata.delay(instance.id, created)
