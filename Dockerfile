FROM python:3.7.9-slim

ARG TARGETARCH

ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y make curl && \
    apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/man \
        /usr/share/doc \
        /usr/share/doc-base

RUN pip install -r requirements.txt && \
    python manage.py collectstatic
RUN (cd client && python setup.py install)
RUN pip install -r docs/requirements.txt && \
    (cd docs && make html) && \
    mv docs/_build/html static/docs && \
    rm -rf docs/_build

ARG KUBECTL_VERSION=v1.19.8
RUN curl -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl && \
    chmod +x /usr/local/bin/kubectl

RUN curl -o /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-${TARGETARCH}/mc && \
    chmod +x /usr/local/bin/mc

VOLUME /db
VOLUME /private
VOLUME /shared

EXPOSE 8000

ENV DJANGO_SECRET %ad&%4*!xpf*$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog
ENV DJANGO_DEBUG 1
ENV KARVDASH_ADMIN_PASSWORD admin
ENV KARVDASH_HTPASSWD_EXPORT_DIR=
ENV KARVDASH_DASHBOARD_TITLE Dashboard
ENV KARVDASH_DASHBOARD_THEME evolve
ENV KARVDASH_ISSUES_URL=
ENV KARVDASH_INGRESS_URL http://localtest.me
ENV KARVDASH_DOCKER_REGISTRY http://127.0.0.1:5000
ENV KARVDASH_DOCKER_REGISTRY_NO_VERIFY=
ENV KARVDASH_DATASETS_AVAILABLE=
ENV KARVDASH_SERVICE_DOMAIN=
ENV KARVDASH_FILES_URL=
ENV KARVDASH_ALLOWED_HOSTPATH_DIRS=

CMD ./start.sh
