# from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.utils.translation import gettext_lazy as _
# from django.core.validators import MinValueValidator
# from users.models import User
# from projects.models import Project

# class Payment(models.Model):
#     STATUS_CHOICES = (
#         ("pending", "Pending"),
#         ("completed", "Completed"),
#         ("failed", "Failed"),
#     )

#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="payments")
#     payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_payments")
#     payee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_payments")
#     amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     payment_date = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

#     class Meta:
#         db_table = "payments"


