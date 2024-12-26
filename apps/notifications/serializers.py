from rest_framework import serializers
from apps.notifications.models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    content_object_str = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'sender', 'message', 'is_read', 
                    'created_at', 'notification_type', 'content_type', 
                    'object_id', 'content_object_str']
        read_only_fields = ['id', 'created_at', 'content_object_str']

    def get_content_object_str(self, obj):
        if obj.content_object:
            return str(obj.content_object)
        return None
        """
        content_type id :
            user : 17
            project : 20
            task : 22
            subscription : 25
        """
class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['user', 'preferences']
