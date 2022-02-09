#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
  echo "Waiting for postgres..."

  while ! nc -z $SQL_HOST $SQL_PORT; do
    sleep 0.1
  done

  echo "PostgreSQL started"

fi
sleep 1

set -m
python manage.py db upgrade
gunicorn project:app -w $((2*4+1)) -b 0.0.0.0:8000 &
# python manage.py run -h 0.0.0.0 --no-debugger --with-threads &
celery -A project.tasks.celery worker -Q queue --concurrency=1 -Ofair --loglevel=info --logfile=project/logs/celery.log -n queue_worker &
celery -A project.tasks.celery worker -Q red  --concurrency=120 --loglevel=info --logfile=project/logs/celery.log -n red_worker &
celery -A project.celery worker -Q green --concurrency=120 --loglevel=info --logfile=project/logs/celery.log -n green_worker &
celery -A project.tasks.celery worker -Q celery_periodic  --loglevel=info --logfile=project/logs/celery.log &
celery -A project.celery beat -l info &
python manage.py create_db 
python manage.py seed_db 
echo 'Druidnet Controller is Ready!'
fg %1
exec "$@"