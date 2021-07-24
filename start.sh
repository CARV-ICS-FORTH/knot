#!/bin/bash

ADMIN_PASSWORD=${KARVDASH_ADMIN_PASSWORD:-admin}

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve
python manage.py createoauthapplication --name vouch --redirect-uri $KARVDASH_VOUCH_URL/auth --secret-name $KARVDASH_VOUCH_SECRET
if [[ -n $KARVDASH_ARGO_URL && -n $KARVDASH_ARGO_NAMESPACE ]]; then
    python manage.py createoauthapplication --name argo --redirect-uri $KARVDASH_ARGO_URL/oauth2/callback --secret-name karvdash-oauth-argo --secret-namespace $KARVDASH_ARGO_NAMESPACE
fi

gunicorn -w 4 -t 60 -b 0.0.0.0:8000 karvdash.wsgi:application
