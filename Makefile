# Copyright [2019] [FORTH-ICS]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

SHELL=/bin/bash

REGISTRY_NAME?=carvicsforth
KUBECTL_VERSION?=v1.15.10

KARVDASH_VERSION=$(shell cat VERSION)
KARVDASH_IMAGE_TAG=$(REGISTRY_NAME)/karvdash:$(KARVDASH_VERSION)
KARVDASH_WEBHOOK_PROXY_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-webhook-proxy:$(KARVDASH_VERSION)

# This should match the version used in Zeppelin templates (we use <Zeppelin version>.<build>).
ZEPPELIN_VERSION=0.9.0.4
ZEPPELIN_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin:$(ZEPPELIN_VERSION)
ZEPPELIN_GPU_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin-gpu:$(ZEPPELIN_VERSION)

DEPLOY_DIR=deploy
DOCKER_DESKTOP_DIR=$(DEPLOY_DIR)/docker-desktop

.PHONY: all prepare-docker-desktop unprepare-docker-desktop deploy-docker-desktop undeploy-docker-desktop deploy-crds undeploy-crds deploy-rbac undeploy-rbac deploy undeploy service-containers service-containers-push containers containers-push

all: containers

$(DOCKER_DESKTOP_DIR)/localtest.me.key $(DOCKER_DESKTOP_DIR)/localtest.me.crt:
	mkdir -p $(DOCKER_DESKTOP_DIR)
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $(DOCKER_DESKTOP_DIR)/localtest.me.key -out $(DOCKER_DESKTOP_DIR)/localtest.me.crt -subj "/CN=*.localtest.me/CN=localtest.me/O=localtest.me"

prepare-docker-desktop: $(DOCKER_DESKTOP_DIR)/localtest.me.key $(DOCKER_DESKTOP_DIR)/localtest.me.crt deploy-crds deploy-rbac
	if [[ `helm version --short` != v3* ]]; then echo "Can not find Helm 3 installed"; exit; fi
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
	helm repo update
	kubectl create secret tls ssl-certificate \
	--cert=$(DOCKER_DESKTOP_DIR)/localtest.me.crt \
	--key=$(DOCKER_DESKTOP_DIR)/localtest.me.key
	helm install ingress ingress-nginx/ingress-nginx --version 2.16.0 --namespace default \
    --set controller.extraArgs.default-ssl-certificate=ingress-nginx/ssl-certificate \
    --set controller.admissionWebhooks.enabled=false
	helm repo add twuni https://helm.twun.io
	helm repo update
	helm install registry twuni/docker-registry --version 1.10.0 --namespace default \
	--set persistence.enabled=true \
	--set persistence.deleteEnabled=true \
	--set service.type=LoadBalancer

unprepare-docker-desktop:
	helm uninstall registry --namespace default
	helm uninstall ingress --namespace default
	kubectl delete secret ssl-certificate

deploy-docker-desktop: prepare-docker-desktop
	# Directories needed for files
	mkdir -p private
	mkdir -p shared
	# Template variables
	IP_ADDRESS=$$(ipconfig getifaddr en0 || ipconfig getifaddr en1); \
	export DJANGO_SECRET="JWFkJiU0KiF4cGYqJHdkM150NTYrI29kZTQ9QHleanVfdCtqOWYrMjBhanN0YV5nb2c="; \
	export DJANGO_DEBUG=1; \
	export KARVDASH_INGRESS_DOMAIN=https://localtest.me; \
	export KARVDASH_IMAGE=$(KARVDASH_IMAGE_TAG); \
	export KARVDASH_WEBHOOK_PROXY_IMAGE=$(KARVDASH_WEBHOOK_PROXY_IMAGE_TAG); \
	export KARVDASH_DASHBOARD_TITLE="Karvdash on Docker Desktop"; \
	export KARVDASH_DASHBOARD_THEME="evolve"; \
	export KARVDASH_DOCKER_REGISTRY="http://$$IP_ADDRESS:5000"; \
	export KARVDASH_DATASETS_AVAILABLE=""; \
	export KARVDASH_PERSISTENT_STORAGE_DIR="$(PWD)/db"; \
	export KARVDASH_PRIVATE_HOST_DIR="$(PWD)/private"; \
	export KARVDASH_SHARED_HOST_DIR="$(PWD)/shared"; \
	export KARVDASH_INGRESS_HOST=$$(echo $$KARVDASH_INGRESS_DOMAIN | sed -e 's,^.*://,,g'); \
	envsubst < $(DEPLOY_DIR)/karvdash.yaml | kubectl apply -f -

undeploy-docker-desktop: unprepare-docker-desktop undeploy

deploy-crds:
	kubectl apply -f $(DEPLOY_DIR)/argo-crd.yaml
	kubectl apply -f $(DEPLOY_DIR)/karvdash-crd.yaml

undeploy-crds:
	kubectl delete -f $(DEPLOY_DIR)/argo-crd.yaml
	kubectl delete -f $(DEPLOY_DIR)/karvdash-crd.yaml

deploy-rbac:
	kubectl apply -f $(DEPLOY_DIR)/discover-base-url-rbac.yaml
	kubectl apply -f $(DEPLOY_DIR)/namespace-view-rbac.yaml

undeploy-rbac:
	kubectl delete -f $(DEPLOY_DIR)/discover-base-url-rbac.yaml
	kubectl delete -f $(DEPLOY_DIR)/namespace-view-rbac.yaml

deploy: deploy-crds deploy-rbac
	# Check for necessary set variables
	if [[ -z $$DJANGO_SECRET ]]; then echo "DJANGO_SECRET is not set"; exit; fi; \
	if [[ -z $$KARVDASH_INGRESS_DOMAIN ]]; then echo "KARVDASH_INGRESS_DOMAIN is not set"; exit; fi; \
	if [[ -z $$KARVDASH_DOCKER_REGISTRY ]]; then echo "KARVDASH_DOCKER_REGISTRY is not set"; exit; fi; \
	if [[ -z $$KARVDASH_PERSISTENT_STORAGE_DIR ]]; then echo "KARVDASH_PERSISTENT_STORAGE_DIR is not set"; exit; fi; \
	if [[ -z $$KARVDASH_PRIVATE_HOST_DIR ]]; then echo "KARVDASH_PRIVATE_HOST_DIR is not set"; exit; fi; \
	if [[ -z $$KARVDASH_SHARED_HOST_DIR ]]; then echo "KARVDASH_SHARED_HOST_DIR is not set"; exit; fi; \
	export DJANGO_DEBUG=$${DJANGO_DEBUG:=""}; \
	export KARVDASH_IMAGE=$(KARVDASH_IMAGE_TAG); \
	export KARVDASH_WEBHOOK_PROXY_IMAGE=$(KARVDASH_WEBHOOK_PROXY_IMAGE_TAG); \
	export KARVDASH_HTPASSWD_EXPORT_DIR=$${KARVDASH_HTPASSWD_EXPORT_DIR:=""}; \
	export KARVDASH_DASHBOARD_TITLE=$${KARVDASH_DASHBOARD_TITLE:="Karvdash"}; \
	export KARVDASH_DASHBOARD_THEME=$${KARVDASH_DASHBOARD_THEME:="evolve"}; \
	export KARVDASH_ISSUES_URL=$${KARVDASH_ISSUES_URL:=""}; \
	export KARVDASH_DOCKER_REGISTRY_NO_VERIFY=$${KARVDASH_DOCKER_REGISTRY_NO_VERIFY:=""}; \
	export KARVDASH_DATASETS_AVAILABLE=$${KARVDASH_DATASETS_AVAILABLE:=""}; \
	export KARVDASH_ALLOWED_HOSTPATH_DIRS=$${KARVDASH_ALLOWED_HOSTPATH_DIRS:=""}; \
	export KARVDASH_INGRESS_HOST=$$(echo $$KARVDASH_INGRESS_DOMAIN | sed -e 's,^.*://,,g'); \
	envsubst < $(DEPLOY_DIR)/karvdash.yaml | kubectl apply -f -

undeploy:
	kubectl delete -f $(DEPLOY_DIR)/karvdash.yaml
	kubectl delete mutatingwebhookconfigurations/karvdash
	kubectl delete validatingwebhookconfigurations/karvdash

service-containers:
	docker build -f containers/zeppelin/Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(ZEPPELIN_IMAGE_TAG) .
	docker build -f containers/zeppelin-gpu/Dockerfile --build-arg BASE=$(ZEPPELIN_IMAGE_TAG) -t $(ZEPPELIN_GPU_IMAGE_TAG) .

service-containers-push:
	docker push $(ZEPPELIN_IMAGE_TAG)
	docker push $(ZEPPELIN_GPU_IMAGE_TAG)

containers:
	docker build -f containers/webhook-proxy/Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KARVDASH_WEBHOOK_PROXY_IMAGE_TAG) .
	docker build -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KARVDASH_IMAGE_TAG) .

containers-push:
	docker push $(KARVDASH_WEBHOOK_PROXY_IMAGE_TAG)
	docker push $(KARVDASH_IMAGE_TAG)
