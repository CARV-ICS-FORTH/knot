#!/bin/bash

if [ ! -f /var/run/secrets/kubernetes.io/serviceaccount/namespace ]; then
    # Running outside Kubernetes, skip SSL and webhook
    exit 0
fi

NAMESPACE=`cat /var/run/secrets/kubernetes.io/serviceaccount/namespace`
SERVER_NAME=karvdash.$NAMESPACE.svc

CERTS_DIR=/db/certs
if [ ! -d $CERTS_DIR ]; then
    mkdir -p $CERTS_DIR
    openssl req -nodes -new -x509 -days 3650 -keyout $CERTS_DIR/ca.key -out $CERTS_DIR/ca.crt -subj "/CN=karvdash CA"
    openssl genrsa -out $CERTS_DIR/server.key 2048
    cat >$CERTS_DIR/csr.conf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
CN = $SERVER_NAME

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $SERVER_NAME

[v3_ext]
authorityKeyIdentifier=keyid,issuer:always
basicConstraints=CA:FALSE
keyUsage=keyEncipherment,dataEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=@alt_names
EOF
    openssl req -new -key $CERTS_DIR/server.key -config $CERTS_DIR/csr.conf | openssl x509 -req -CA $CERTS_DIR/ca.crt -CAkey $CERTS_DIR/ca.key -set_serial 01 -days 3650 -extensions v3_ext -extfile $CERTS_DIR/csr.conf -out $CERTS_DIR/server.crt
    rm $CERTS_DIR/csr.conf
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

cat >/etc/nginx/conf.d/default.conf <<EOF
server {
    listen 443 ssl;
    server_name $SERVER_NAME;

    ssl_certificate         $CERTS_DIR/server.crt;
    ssl_certificate_key     $CERTS_DIR/server.key;

    ssl_session_cache       builtin:1000 shared:SSL:10m;
    ssl_protocols           TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers             HIGH:!aNULL:!eNULL:!EXPORT:!CAMELLIA:!DES:!MD5:!PSK:!RC4;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_set_header    Host \$host;
        proxy_set_header    X-Real-IP \$remote_addr;
        proxy_set_header    X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto \$scheme;

        # Fix the “It appears that your reverse proxy set up is broken" error.
        proxy_pass          http://127.0.0.1:80;
        proxy_read_timeout  30;

        proxy_redirect      http://127.0.0.1:80 https://$SERVER_NAME;
    }
}
EOF
