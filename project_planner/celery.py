from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_planner.settings')

app = Celery('project_planner')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks from installed apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS + ['core.tasks'])

app.conf.beat_schedule = {
    'check_due_dates_every_hour': {
        'task': 'core.tasks.check_overdue_items',
        'schedule': crontab(minute=0, hour='*'),
    },
}
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# To run the worker, use the following command:
# celery -A project_planner worker --loglevel=info