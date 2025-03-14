#!/bin/bash

update-ca-certificates
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

TYPE=${1:-server}

if [[ $TYPE == "worker" ]]; then
    celery -A knot worker -l info
    exit $?
fi

ADMIN_PASSWORD=${KNOT_ADMIN_PASSWORD:-admin}
TIMEOUT=${KNOT_TIMEOUT:-180}

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve
python manage.py createoauthapplication --name vouch --redirect-uri $KNOT_VOUCH_URL/auth --secret-name $KNOT_VOUCH_SECRET --secret-namespace $KNOT_NAMESPACE
if [[ -n $KNOT_JUPYTERHUB_URL && -n $KNOT_JUPYTERHUB_NAMESPACE ]]; then
    python manage.py createoauthapplication --name jupyterhub --redirect-uri $KNOT_JUPYTERHUB_URL/hub/oauth_callback --secret-name knot-oauth-jupyterhub --secret-namespace $KNOT_JUPYTERHUB_NAMESPACE
fi
if [[ -n $KNOT_ARGO_WORKFLOWS_URL && -n $KNOT_ARGO_WORKFLOWS_NAMESPACE ]]; then
    python manage.py createoauthapplication --name argo --redirect-uri $KNOT_ARGO_WORKFLOWS_URL/oauth2/callback --secret-name knot-oauth-argo --secret-namespace $KNOT_ARGO_WORKFLOWS_NAMESPACE
fi
if [[ -n $KNOT_HARBOR_URL && -n $KNOT_HARBOR_NAMESPACE && -n $KNOT_HARBOR_ADMIN_PASSWORD ]]; then
    python manage.py createoauthapplication --name harbor --redirect-uri $KNOT_HARBOR_URL/c/oidc/callback --secret-name knot-oauth-harbor --secret-namespace $KNOT_HARBOR_NAMESPACE
    python manage.py configureharbor --secret-name knot-oauth-harbor --secret-namespace $KNOT_HARBOR_NAMESPACE --harbor-url $KNOT_HARBOR_URL --harbor-admin-password `printf "%q" $KNOT_HARBOR_ADMIN_PASSWORD` --ingress-url $KNOT_INGRESS_URL || exit 1

    # Upload service charts
    package_charts () {
        for chart in `ls -d ../services/*/`; do
            if [[ -n $KNOT_DISABLED_SERVICES_FILE ]] && grep -iq '^'$(basename $chart)'$' $KNOT_DISABLED_SERVICES_FILE; then
                continue
            fi
            helm package $chart
        done
    }

    upload_charts () {
        for chart in `ls *.tgz`; do
            helm push $chart oci://$(basename $KNOT_HARBOR_URL)/library
        done
    }

    echo -n "$KNOT_HARBOR_ADMIN_PASSWORD" | helm registry login --username=admin --password-stdin $(basename $KNOT_HARBOR_URL)
    (mkdir -p repo/services-build && cd repo/services-build && package_charts && upload_charts)
fi
if [[ -n $KNOT_GRAFANA_URL && -n $KNOT_GRAFANA_NAMESPACE ]]; then
    python manage.py createoauthapplication --name grafana --redirect-uri $KNOT_GRAFANA_URL/login/generic_oauth --secret-name knot-oauth-grafana --secret-namespace $KNOT_GRAFANA_NAMESPACE
fi

gunicorn -w 4 -t $TIMEOUT -b 0.0.0.0:8000 knot.wsgi:application &
daphne -b 0.0.0.0 -p 8001 knot.asgi:application &
wait -n
exit $?
