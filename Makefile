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
KUBECTL_VERSION?=v1.19.8

KARVDASH_VERSION=$(shell cat VERSION)
KARVDASH_IMAGE_TAG=$(REGISTRY_NAME)/karvdash:$(KARVDASH_VERSION)

# This should match the version used in Zeppelin templates (we use <Zeppelin version>.<build>).
ZEPPELIN_VERSION=0.9.0.5
ZEPPELIN_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin:$(ZEPPELIN_VERSION)
ZEPPELIN_GPU_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin-gpu:$(ZEPPELIN_VERSION)

DEPLOY_DIR=deploy
CHART_DIR=./chart/karvdash

.PHONY: all prepare-docker-desktop unprepare-docker-desktop deploy-docker-desktop undeploy-docker-desktop undeploy-crds service-containers service-containers-push container container-push

all: container

$(DEPLOY_DIR)/localtest.me.key $(DEPLOY_DIR)/localtest.me.crt:
	mkdir -p $(DEPLOY_DIR)
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $(DEPLOY_DIR)/localtest.me.key -out $(DEPLOY_DIR)/localtest.me.crt -subj "/CN=*.localtest.me/CN=localtest.me/O=localtest.me"

prepare-docker-desktop: $(DEPLOY_DIR)/localtest.me.key $(DEPLOY_DIR)/localtest.me.crt
	if [[ `helm version --short` != v3* ]]; then echo "Can not find Helm 3 installed"; exit; fi
	helm repo add jetstack https://charts.jetstack.io
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
	helm repo add twuni https://helm.twun.io
	helm repo update
	helm list -q | grep cert-manager || \
	helm install cert-manager jetstack/cert-manager --version v1.1.0 --namespace default \
	--set installCRDs=true
	kubectl get secret ssl-certificate || \
	kubectl create secret tls ssl-certificate \
	--cert=$(DEPLOY_DIR)/localtest.me.crt \
	--key=$(DEPLOY_DIR)/localtest.me.key
	helm list -q | grep ingress || \
	helm install ingress ingress-nginx/ingress-nginx --version 3.19.0 --namespace default \
    --set controller.extraArgs.default-ssl-certificate=default/ssl-certificate \
    --set controller.admissionWebhooks.enabled=false
	helm list -q | grep registry || \
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
	IP_ADDRESS=$$(ipconfig getifaddr en0 || ipconfig getifaddr en1); \
	helm list -q | grep karvdash || \
	helm install karvdash $(CHART_DIR) --namespace default \
	--set image.namespace="$(REGISTRY_NAME)" \
	--set image.tag="$(KARVDASH_VERSION)" \
	--set karvdash.djangoSecret="JWFkJiU0KiF4cGYqJHdkM150NTYrI29kZTQ9QHleanVfdCtqOWYrMjBhanN0YV5nb2c=" \
	--set karvdash.djangoDebug="1" \
	--set karvdash.dashboardTitle="Karvdash on Docker Desktop" \
	--set karvdash.ingressURL="https://localtest.me" \
 	--set karvdash.dockerRegistry="http://$$IP_ADDRESS:5000" \
	--set karvdash.persistentStorageDir="$(PWD)/db" \
	--set karvdash.filesURL="file://$(PWD)"

undeploy-crds:
	kubectl delete -f $(CHART_DIR)/crds/argo-crd.yaml
	kubectl delete -f $(CHART_DIR)/crds/karvdash-crd.yaml

undeploy-docker-desktop: unprepare-docker-desktop undeploy-crds
	helm uninstall karvdash --namespace default

service-containers:
	docker build -f containers/zeppelin/Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(ZEPPELIN_IMAGE_TAG) .
	docker build -f containers/zeppelin-gpu/Dockerfile --build-arg BASE=$(ZEPPELIN_IMAGE_TAG) -t $(ZEPPELIN_GPU_IMAGE_TAG) .

service-containers-push:
	docker push $(ZEPPELIN_IMAGE_TAG)
	docker push $(ZEPPELIN_GPU_IMAGE_TAG)

container:
	docker build -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KARVDASH_IMAGE_TAG) .

container-push:
	docker push $(KARVDASH_IMAGE_TAG)
