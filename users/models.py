from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils.deconstruct import deconstructible
# from .utils import resize_image
import os

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("member", "Member"),
    )

    SUBSCRIPTION_CHOICES = (
        ("free", "Free"),
        ("standard", "Standard"),
        ("enterprise", "Enterprise"),
    )

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    subscription_type = models.CharField(
        max_length=20, choices=SUBSCRIPTION_CHOICES, default="free"
    )

    REQUIRED_FIELDS = ["email"]


# @deconstructible
# class PathAndRename:
#     def __init__(self, path):
#         self.path = path

#     def __call__(self, instance, filename):
#         ext = filename.split('.')[-1]
        
#         username = instance.user.username

#         count = instance.profile_picture_change_count
#         filename = f'pp_{username}_{count}.{ext}'
        
#         return os.path.join(self.path, str(instance.user.id), filename)

class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profilePicture = models.ImageField(default='default.png')
    profile_picture_change_count = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        # if self.pk:
        #     old_profile = Profile.objects.get(pk=self.pk)
        #     if old_profile.profilePicture and old_profile.profilePicture.name != self.profilePicture.name:
        #         if old_profile.profilePicture.name != 'default.png':
        #             old_profile.profilePicture.delete(save=False)
                
        #         self.profile_picture_change_count += 1
        #         self.profilePicture = resize_image(self.profilePicture)
        # else:
        #     if self.profilePicture:
        #         self.profilePicture = resize_image(self.profilePicture)
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username
    
    class Meta:
        db_table = "profiles"