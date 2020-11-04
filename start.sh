#!/bin/bash

ADMIN_PASSWORD=${KARVDASH_ADMIN_PASSWORD:-admin}

export KARVDASH_DATABASE_DIR=/db
export KARVDASH_PRIVATE_DIR=/private
export KARVDASH_SHARED_DIR=/shared
export KARVDASH_SERVICE_TEMPLATE_DIR=/db/templates
export KARVDASH_SERVICE_DATABASE_DIR=/db/services

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve

gunicorn -w 4 -b 0.0.0.0:80 karvdash.wsgi:application
