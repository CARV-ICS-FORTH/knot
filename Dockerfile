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
ENV GENOME_ADMIN_PASSWORD admin
ENV GENOME_DOCKER_REGISTRY http://127.0.0.1:5000
ENV GENOME_LOCAL_HOST_DIR=
ENV GENOME_REMOTE_HOST_DIR=
ENV GENOME_SHARED_HOST_DIR=

CMD ./start.sh
