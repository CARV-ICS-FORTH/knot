#!/bin/bash

ADMIN_PASSWORD=${KARVDASH_ADMIN_PASSWORD:-admin}

export KARVDASH_DATABASE_DIR=/db
export KARVDASH_PRIVATE_DIR=/private
export KARVDASH_SHARED_DIR=/shared
export KARVDASH_SERVICE_DATABASE_DIR=/db/services

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve
python manage.py runserver --insecure 0.0.0.0:80
