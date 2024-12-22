# Generated by Django 5.1.4 on 2024-12-22 07:00

import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=6)),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('stripe_payment_intent_id', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('basic', 'Basic'), ('pro', 'Pro'), ('enterprise', 'Enterprise')], max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=6)),
                ('duration_days', models.PositiveIntegerField(default=30)),
                ('stripe_price_id', models.CharField(max_length=100, unique=True)),
                ('max_projects', models.IntegerField(validators=[django.core.validators.MinValueValidator(-1)])),
                ('max_members_per_project', models.IntegerField(validators=[django.core.validators.MinValueValidator(-1)])),
            ],
        ),
    ]