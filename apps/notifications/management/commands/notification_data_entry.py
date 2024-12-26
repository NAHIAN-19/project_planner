from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.notifications.models import NotificationPreference

class Command(BaseCommand):
    help = 'Creates notification preferences for existing users'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        users_without_preferences = User.objects.filter(notification_preferences=None)
        
        for user in users_without_preferences:
            NotificationPreference.objects.create(user=user)
            self.stdout.write(f'Created preferences for user {user.username}')
