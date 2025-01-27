import secrets
import os
import django
from django.core.management import call_command

def generate_secret_key():
    """Generate a random secret key."""
    return ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50))

def create_env_file():
    """Automatically create a .env file with generated credentials and default settings."""
    secret_key = generate_secret_key()
    env_content = f"""
SECRET_KEY={secret_key}
REDIS_PASSWORD=your-redis-password
# Email settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-app-password
# to get EMAIL_HOST_PASSWORD follow this link : https://www.geeksforgeeks.org/setup-sending-email-in-django-project/

# Stripe settings
STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=whsec_your-stripe-webhook-secret
"""
    with open(".env", "w") as env_file:
        env_file.write(env_content)
    
    print(".env file created with generated credentials.")

def run_subscription_data_command():
    """Run the subscription_data management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_planner.settings")
    django.setup()  # Initialize Django
    try:
        print("Running subscription_data command...")
        call_command("subscription_data") 
        print("subscription_data command executed successfully.")
    except Exception as e:
        print(f"Error while running subscription_data command: {e}")

if __name__ == "__main__":
    print("Starting setup...")
    
    # Step 1: Generate .env file
    create_env_file()
    
    # Step 2: Run the subscription_data management command
    run_subscription_data_command()
    
    print("Setup completed successfully.")
