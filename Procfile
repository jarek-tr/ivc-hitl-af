web: gunicorn ivc_hitl_af.wsgi --bind 0.0.0.0:$PORT --chdir backend
worker: celery -A ivc_hitl_af worker -l INFO -Q default,mturk --workdir backend
beat: celery -A ivc_hitl_af beat -l INFO --workdir backend
