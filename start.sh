#!/bin/bash

ADMIN_PASSWORD=${KARVDASH_ADMIN_PASSWORD:-admin}

export KARVDASH_DATABASE_DIR=/db
export KARVDASH_PRIVATE_DIR=/private
export KARVDASH_SHARED_DIR=/shared
export KARVDASH_SERVICE_TEMPLATE_DIR=/db/templates
export KARVDASH_SERVICE_DATABASE_DIR=/db/services

python manage.py migrate
python manage.py createadmin --noinput --username admin --password $ADMIN_PASSWORD --email admin@example.com --preserve

if [ ! -f /var/run/secrets/kubernetes.io/serviceaccount/namespace ]; then
    # Running outside Kubernetes, skip SSL and webhook
    uwsgi --ini uwsgi/karvdash.ini
    exit 0
fi

NAMESPACE=`cat /var/run/secrets/kubernetes.io/serviceaccount/namespace`
SERVER_NAME=karvdash.$NAMESPACE.svc

CERTS_DIR=/db/certs
if [ ! -d $CERTS_DIR ]; then
    mkdir -p $CERTS_DIR
    openssl genrsa -out $CERTS_DIR/server.key 2048
    openssl req -nodes -new -x509 -keyout $CERTS_DIR/ca.key -out $CERTS_DIR/ca.crt -subj "/CN=karvdash CA"
    openssl req -new -key $CERTS_DIR/server.key -subj "/CN=$SERVER_NAME" | openssl x509 -req -CA $CERTS_DIR/ca.crt -CAkey $CERTS_DIR/ca.key -set_serial 01 -out $CERTS_DIR/server.crt
fi

CA_BUNDLE=`cat $CERTS_DIR/ca.crt | base64 -w 0`

cat >/db/webhook.yaml <<EOF
apiVersion: admissionregistration.k8s.io/v1beta1
kind: MutatingWebhookConfiguration
metadata:
  name: karvdash
  labels:
    app: karvdash
webhooks:
  - name: $SERVER_NAME
    clientConfig:
      caBundle: $CA_BUNDLE
      service:
        name: karvdash
        namespace: $NAMESPACE
        path: "/webhooks/mutate"
    rules:
      - operations: ["CREATE"]
        apiGroups: ["*"]
        apiVersions: ["*"]
        resources: ["pods", "deployments"]
    namespaceSelector:
      matchLabels:
        karvdash: enabled
    failurePolicy: Fail
---
apiVersion: admissionregistration.k8s.io/v1beta1
kind: ValidatingWebhookConfiguration
metadata:
  name: karvdash
  labels:
    app: karvdash
webhooks:
  - name: $SERVER_NAME
    clientConfig:
      caBundle: $CA_BUNDLE
      service:
        name: karvdash
        namespace: $NAMESPACE
        path: "/webhooks/validate"
    rules:
      - operations: ["CREATE"]
        apiGroups: ["*"]
        apiVersions: ["*"]
        resources: ["pods", "deployments"]
    namespaceSelector:
      matchLabels:
        karvdash: enabled
    failurePolicy: Fail
EOF

kubectl apply -n $NAMESPACE -f /db/webhook.yaml
uwsgi --emperor uwsgi
