ARG BASE=apache/zeppelin:0.9.0
FROM ${BASE}

USER root

ARG KUBECTL_VERSION=v1.19.8
RUN curl -sSL -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
    chmod +x /usr/local/bin/kubectl

RUN curl -sSL -o /usr/local/bin/argo.gz https://github.com/argoproj/argo/releases/download/v2.12.10/argo-linux-amd64.gz && \
    gunzip /usr/local/bin/argo.gz && \
    chmod +x /usr/local/bin/argo

RUN curl -L -o /tmp/spark-2.4.5-bin-hadoop2.7.tgz https://archive.apache.org/dist/spark/spark-2.4.5/spark-2.4.5-bin-hadoop2.7.tgz && \
    (cd /opt && tar -zxvf /tmp/spark-2.4.5-bin-hadoop2.7.tgz && ln -s spark-2.4.5-bin-hadoop2.7 spark) && \
    rm -f /tmp/spark-2.4.5-bin-hadoop2.7.tgz

RUN mkdir /root/client
COPY client /root/client/
RUN (cd /root/client && ./setup.py install) && \
    rm -rf /root/client

ARG EVOLVE_LIBRARY_COMMIT=4eab32f87b33
RUN curl -sLO https://bitbucket.org/sunlightio/evolve_python_library/get/${EVOLVE_LIBRARY_COMMIT}.tar.gz && \
    tar -zxvf ${EVOLVE_LIBRARY_COMMIT}.tar.gz && \
    (cd sunlightio-evolve_python_library-${EVOLVE_LIBRARY_COMMIT} && python setup.py install) && \
    rm -rf ${EVOLVE_LIBRARY_COMMIT}.tar.gz sunlightio-evolve_python_library-${EVOLVE_LIBRARY_COMMIT}

COPY containers/zeppelin/interpreter.json /opt/zeppelin/conf/
COPY containers/zeppelin/start.sh /opt/zeppelin/

ENV KARVDASH_NAMESPACE=

CMD ["/opt/zeppelin/start.sh"]
