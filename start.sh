#!/bin/bash

ADMIN_PASSWORD=${GENOME_ADMIN_PASSWORD:-admin}

export GENOME_DATABASE_DIR=/db
export GENOME_LOCAL_DIR=/local
export GENOME_REMOTE_DIR=/remote
export GENOME_SHARED_DIR=/shared
export GENOME_SERVICE_DATABASE_DIR=/db/services

python manage.py migrate
python manage.py createadmin  --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve
python manage.py runserver 0.0.0.0:8000
