#!/bin/bash

ADMIN_PASSWORD=${KARVDASH_ADMIN_PASSWORD:-admin}

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve
python manage.py createvouchoauthapplication

gunicorn -w 4 -t 60 -b 0.0.0.0:8000 karvdash.wsgi:application
