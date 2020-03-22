FROM python:3.7

ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

RUN curl -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v1.14.8/bin/linux/amd64/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN apt-get update
RUN apt-get install -y docker.io

VOLUME /db
VOLUME /local
VOLUME /remote
VOLUME /shared

EXPOSE 8000

ENV DJANGO_SECRET %ad&%4*!xpf*$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog
ENV DJANGO_DEBUG=1
ENV KARVDASH_ADMIN_PASSWORD admin
ENV KARVDASH_DASHBOARD_TITLE=
ENV KARVDASH_DASHBOARD_THEME=
ENV KARVDASH_INGRESS_DOMAIN localtest.me
ENV KARVDASH_SERVICE_REDIRECT_SSL=
ENV KARVDASH_DOCKER_REGISTRY http://127.0.0.1:5000
ENV KARVDASH_LOCAL_HOST_DIR=
ENV KARVDASH_REMOTE_HOST_DIR=
ENV KARVDASH_SHARED_HOST_DIR=

CMD ./start.sh
