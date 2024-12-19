from core.tasks import send_email
class EmailService:
    """
    Service to handle email-related operations, such as sending OTP emails.
    """
    def send_otp_email(self, otp, email):
        """
        Send OTP code to the user's email.
        Args:
            otp (str): The OTP code to send.
            email (str): The recipient's email address.
        """
        subject = "Your OTP Code"
        message = f"Your OTP code is {otp}."
        send_email.delay(subject, message, email)
        
    def send_payment_status_email(self, status, payment_id):
        from apps.subscriptions.models import SubscriptionPayment
        payment = SubscriptionPayment.objects.get(id=payment_id)
        if status == "completed":
            subject = 'Payment Success',
            message = f'Your payment of {payment.amount} {payment.currency} was successful.'
        elif status == "failed":
            subject = 'Payment Failed',
            message = f'Your payment of {payment.amount} {payment.currency} has failed.',
        else:
            return
        recipient = payment.subscription.user.email
        send_email.delay(subject, message, recipient)