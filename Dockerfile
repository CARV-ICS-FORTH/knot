FROM python:3.7

ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt && \
    python manage.py collectstatic
RUN (cd client && python setup.py install)
RUN pip install -r docs/requirements.txt && \
    (cd docs && make html) && \
    mv docs/_build/html static/docs && \
    rm -rf docs/_build

ARG KUBECTL_VERSION=v1.15.10
RUN curl -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN apt-get update
RUN apt-get install -y docker.io

VOLUME /db
VOLUME /private
VOLUME /shared

EXPOSE 80

ENV DJANGO_SECRET %ad&%4*!xpf*$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog
ENV DJANGO_DEBUG 1
ENV KARVDASH_ADMIN_PASSWORD admin
ENV KARVDASH_HTPASSWD_EXPORT_DIR=
ENV KARVDASH_DASHBOARD_TITLE Dashboard
ENV KARVDASH_DASHBOARD_THEME evolve
ENV KARVDASH_ISSUES_URL=
ENV KARVDASH_INGRESS_DOMAIN localtest.me
ENV KARVDASH_SERVICE_REDIRECT_SSL=
ENV KARVDASH_DOCKER_REGISTRY http://127.0.0.1:5000
ENV KARVDASH_DOCKER_REGISTRY_NO_VERIFY=
ENV KARVDASH_DATASETS_AVAILABLE=
ENV KARVDASH_API_BASE_URL=
ENV KARVDASH_PRIVATE_HOST_DIR=
ENV KARVDASH_SHARED_HOST_DIR=

CMD ./start.sh
