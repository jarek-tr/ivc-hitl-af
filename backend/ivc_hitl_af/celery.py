import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ivc_hitl_af.settings")

app = Celery("ivc_hitl_af")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
