FROM nginx:1.19.3

ARG KUBECTL_VERSION=v1.15.10
RUN curl -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
    chmod +x /usr/local/bin/kubectl

COPY containers/webhook-proxy/30-configure-webhooks.sh /docker-entrypoint.d/30-configure-webhooks.sh
