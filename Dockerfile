FROM python:3.8.12 AS ldap-build

RUN apt-get update -y && \
    apt-get install -y libsasl2-dev python-dev libldap2-dev libssl-dev && \
    python -m pip wheel --wheel-dir=/tmp python-ldap==3.4.0

FROM python:3.8.12-slim

ARG TARGETARCH

ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y make curl vim-tiny procps && \
    apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/man \
        /usr/share/doc \
        /usr/share/doc-base

ARG KUBECTL_VERSION=v1.22.4
RUN curl -Lo /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl && \
    chmod +x /usr/local/bin/kubectl

ARG GO_CONTAINERREGISTRY_VERSION=v0.5.1
RUN if [ "${TARGETARCH}" = "amd64" ]; then \
    curl -Lo /tmp/go-containerregistry.tar.gz https://github.com/google/go-containerregistry/releases/download/${GO_CONTAINERREGISTRY_VERSION}/go-containerregistry_Linux_x86_64.tar.gz; \
    else \
    curl -Lo /tmp/go-containerregistry.tar.gz https://github.com/google/go-containerregistry/releases/download/${GO_CONTAINERREGISTRY_VERSION}/go-containerregistry_Linux_${TARGETARCH}.tar.gz; \
    fi && \
    (cd /usr/local/bin && tar zxvf /tmp/go-containerregistry.tar.gz crane) && \
    rm -rf /tmp/go-containerregistry.tar.gz

COPY . /app
WORKDIR /app

COPY --from=ldap-build /tmp/*.whl /tmp
RUN pip install /tmp/*.whl
RUN pip install -r requirements.txt && \
    python manage.py collectstatic
RUN (cd client && python setup.py install)
RUN pip install -r docs/requirements.txt && \
    (cd docs && make html) && \
    mv docs/_build/html static/docs && \
    rm -rf docs/_build

VOLUME /db
VOLUME /files

EXPOSE 8000

ENV DJANGO_SECRET %ad&%4*!xpf*$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog
ENV DJANGO_DEBUG 1
ENV KARVDASH_DATABASE_DIR /db
ENV KARVDASH_TIMEOUT 180
ENV KARVDASH_ADMIN_PASSWORD admin
ENV KARVDASH_NAMESPACE default
ENV KARVDASH_LDAP_SERVER_URL=
ENV KARVDASH_LDAP_USER_DN_TEMPLATE=
ENV KARVDASH_LDAP_USER_ATTR_MAP=
ENV KARVDASH_VOUCH_URL=
ENV KARVDASH_VOUCH_SECRET=
ENV KARVDASH_HTPASSWD_EXPORT_DIR=
ENV KARVDASH_DASHBOARD_TITLE Karvdash
ENV KARVDASH_DOCUMENTATION_URL=
ENV KARVDASH_ISSUES_URL=
ENV KARVDASH_INGRESS_URL http://localtest.me
ENV KARVDASH_REGISTRY_URL=
ENV KARVDASH_REGISTRY_CERT_FILE=
ENV KARVDASH_DATASETS_AVAILABLE=
ENV KARVDASH_SERVICE_DOMAIN=
ENV KARVDASH_FILES_URL=
ENV KARVDASH_FILES_MOUNT_DIR /files
ENV KARVDASH_ALLOWED_HOSTPATH_DIRS=
ENV KARVDASH_DISABLED_SERVICE_TEMPLATES_FILE=
ENV KARVDASH_DISABLED_DATASET_TEMPLATES_FILE=
ENV KARVDASH_SERVICE_URL_PREFIXES_FILE=
ENV KARVDASH_JUPYTERHUB_URL=
ENV KARVDASH_JUPYTERHUB_NAMESPACE=
ENV KARVDASH_JUPYTERHUB_NOTEBOOK_DIR=
ENV KARVDASH_ARGO_WORKFLOWS_URL=
ENV KARVDASH_ARGO_WORKFLOWS_NAMESPACE=

CMD ./start.sh
