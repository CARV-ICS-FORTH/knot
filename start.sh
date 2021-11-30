#!/bin/bash

ADMIN_PASSWORD=${KARVDASH_ADMIN_PASSWORD:-admin}
TIMEOUT=${KARVDASH_TIMEOUT:-180}

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve
python manage.py createoauthapplication --name vouch --redirect-uri $KARVDASH_VOUCH_URL/auth --secret-name $KARVDASH_VOUCH_SECRET --secret-namespace $KARVDASH_NAMESPACE
if [[ -n $KARVDASH_JUPYTERHUB_URL && -n $KARVDASH_JUPYTERHUB_NAMESPACE ]]; then
    python manage.py createoauthapplication --name jupyterhub --redirect-uri $KARVDASH_JUPYTERHUB_URL/hub/oauth_callback --secret-name karvdash-oauth-jupyterhub --secret-namespace $KARVDASH_JUPYTERHUB_NAMESPACE
fi
if [[ -n $KARVDASH_ARGO_WORKFLOWS_URL && -n $KARVDASH_ARGO_WORKFLOWS_NAMESPACE ]]; then
    python manage.py createoauthapplication --name argo --redirect-uri $KARVDASH_ARGO_WORKFLOWS_URL/oauth2/callback --secret-name karvdash-oauth-argo --secret-namespace $KARVDASH_ARGO_WORKFLOWS_NAMESPACE
fi

gunicorn -w 4 -t $TIMEOUT -b 0.0.0.0:8000 karvdash.wsgi:application
