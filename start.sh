#!/bin/bash

update-ca-certificates
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

TYPE=${1:-server}

if [[ $TYPE == "worker" ]]; then
    celery -A karvdash worker -l info
    exit $?
fi

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
if [[ -n $KARVDASH_HARBOR_URL && -n $KARVDASH_HARBOR_NAMESPACE && -n $KARVDASH_HARBOR_ADMIN_PASSWORD ]]; then
    python manage.py createoauthapplication --name harbor --redirect-uri $KARVDASH_HARBOR_URL/c/oidc/callback --secret-name karvdash-oauth-harbor --secret-namespace $KARVDASH_HARBOR_NAMESPACE
    python manage.py configureharbor --oauth-application-name harbor --harbor-url $KARVDASH_HARBOR_URL --harbor-admin-password `printf "%q" $KARVDASH_HARBOR_ADMIN_PASSWORD` --ingress-url $KARVDASH_INGRESS_URL
fi
if [[ -n $KARVDASH_GRAFANA_URL && -n $KARVDASH_GRAFANA_NAMESPACE ]]; then
    python manage.py createoauthapplication --name grafana --redirect-uri $KARVDASH_GRAFANA_URL/login/generic_oauth --secret-name karvdash-oauth-grafana --secret-namespace $KARVDASH_GRAFANA_NAMESPACE
fi
if [[ -n $KARVDASH_OPENBIO_URL && -n $KARVDASH_OPENBIO_NAMESPACE ]]; then
    python manage.py createoauthapplication --name openbio --redirect-uri $KARVDASH_OPENBIO_URL/platform/complete/karvdash/ --secret-name karvdash-oauth-openbio --secret-namespace $KARVDASH_OPENBIO_NAMESPACE
fi

gunicorn -w 4 -t $TIMEOUT -b 0.0.0.0:8000 karvdash.wsgi:application
