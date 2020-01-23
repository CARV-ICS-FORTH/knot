FROM python:3.7

ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

VOLUME /db
VOLUME /local
VOLUME /remote

EXPOSE 8000

ENV DJANGO_SECRET %ad&%4*!xpf*$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog
ENV GENOME_ADMIN_PASSWORD admin

CMD ./start.sh
