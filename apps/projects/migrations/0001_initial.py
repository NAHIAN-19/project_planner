# Generated by Django 5.1.4 on 2024-12-22 07:00

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('total_tasks', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('on_hold', 'On Hold')], default='not_started', max_length=20)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('total_member_count', models.PositiveIntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name='ProjectMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('total_tasks', models.PositiveIntegerField(default=0)),
                ('completed_tasks', models.PositiveIntegerField(default=0)),
            ],
        ),
    ]
