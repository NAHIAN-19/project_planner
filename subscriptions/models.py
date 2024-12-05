from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Subscription(models.Model):
    SUBSCRIPTION_CHOICES = (
        ("free", "Free"),
        ("standard", "Standard"),
        ("enterprise", "Enterprise"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    subscription_type = models.CharField(
        max_length=20, choices=SUBSCRIPTION_CHOICES, default="free"
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=(
        ("active", "Active"),
        ("inactive", "Inactive"),
    ))

    class Meta:
        db_table = "subscriptions"