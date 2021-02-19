ARG BASE=apache/zeppelin:0.9.0
FROM ${BASE}

USER root

ARG KUBECTL_VERSION=v1.15.10
RUN curl -sSL -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl
RUN chmod +x /usr/local/bin/kubectl

RUN curl -sSL -o /usr/local/bin/argo.gz https://github.com/argoproj/argo/releases/download/v2.10.1/argo-linux-amd64.gz
RUN gunzip /usr/local/bin/argo.gz && \
    chmod +x /usr/local/bin/argo

RUN curl -L -o /tmp/spark-2.4.5-bin-hadoop2.7.tgz https://archive.apache.org/dist/spark/spark-2.4.5/spark-2.4.5-bin-hadoop2.7.tgz
RUN (cd /opt && tar -zxvf /tmp/spark-2.4.5-bin-hadoop2.7.tgz && ln -s spark-2.4.5-bin-hadoop2.7 spark) && \
    rm -f /tmp/spark-2.4.5-bin-hadoop2.7.tgz

RUN mkdir /root/client
COPY client /root/client/
RUN (cd /root/client && ./setup.py install) && \
    rm -rf /root/client

RUN git clone https://bitbucket.org/sunlightio/evolve_python_library.git && \
    (cd evolve_python_library && git checkout 4eab32f && python setup.py install) && \
    rm -rf evolve_python_library

COPY containers/zeppelin/interpreter.json /zeppelin/conf/
COPY containers/zeppelin/start.sh /zeppelin/

ENV KARVDASH_NAMESPACE=

CMD ["/zeppelin/start.sh"]
