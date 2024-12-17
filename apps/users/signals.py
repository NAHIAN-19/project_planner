# Signal to create a profile when a user is created
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import Profile, UserMetadata, User

User = settings.AUTH_USER_MODEL
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        

@receiver(post_save, sender=User)
def create_or_update_user_metadata(sender, instance, created, **kwargs):
    if created:
        UserMetadata.objects.create(
            user=instance,
            username=instance.username,
            email=instance.email,
            profile_picture=instance.profile_picture.url if instance.profile_picture else None
        )
    else:
        metadata, _ = UserMetadata.objects.get_or_create(user=instance)
        metadata.username = instance.username
        metadata.email = instance.email
        metadata.profile_picture = instance.profile_picture.url if instance.profile_picture else None
        metadata.save()