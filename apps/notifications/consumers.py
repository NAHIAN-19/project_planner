import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            self.group_name = f"notifications_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        # Error handling for message formatting
        try:
            message = event['message']
            if not isinstance(message, dict):
                raise ValueError("Message must be a dictionary.")
            await self.send(text_data=json.dumps(message))
        except Exception as e:
            # Handle any errors that occur during message sending
            await self.close()
            print(f"Error sending notification: {e}")
        # Send notification data to WebSocket client
        await self.send(text_data=json.dumps(event['message']))
