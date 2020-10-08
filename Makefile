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

REGISTRY_NAME?=carvicsforth
KUBECTL_VERSION?=v1.15.10

KARVDASH_VERSION=$(shell cat VERSION)
KARVDASH_IMAGE_TAG=$(REGISTRY_NAME)/karvdash:$(KARVDASH_VERSION)

# This should match the version used in the Zeppelin template (we use <Zeppelin version>.<build>).
ZEPPELIN_VERSION=0.9.0.4
ZEPPELIN_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin:$(ZEPPELIN_VERSION)

DEPLOY_DIR=deploy
DOCKER_DESKTOP_DIR=$(DEPLOY_DIR)/docker-desktop

define INGRESS_SECRET
apiVersion: v1
kind: Secret
type: kubernetes.io/tls
metadata:
  name: ssl-certificate
  namespace: ingress-nginx
data:
  tls.crt: CERT
  tls.key: KEY
endef

.PHONY: all prepare-docker-desktop unprepare-docker-desktop deploy-docker-desktop undeploy-docker-desktop deploy-crds undeploy-crds deploy undeploy container push

all: container push

$(DOCKER_DESKTOP_DIR)/localtest.me.key $(DOCKER_DESKTOP_DIR)/localtest.me.crt:
	mkdir -p $(DOCKER_DESKTOP_DIR)
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $(DOCKER_DESKTOP_DIR)/localtest.me.key -out $(DOCKER_DESKTOP_DIR)/localtest.me.crt -subj "/CN=*.localtest.me/CN=localtest.me/O=localtest.me"

export INGRESS_SECRET
$(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml: $(DOCKER_DESKTOP_DIR)/localtest.me.key $(DOCKER_DESKTOP_DIR)/localtest.me.crt
	# Get the ingress parts
	curl https://raw.githubusercontent.com/kubernetes/ingress-nginx/nginx-0.30.0/deploy/static/mandatory.yaml > $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	echo "---" >> $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	curl https://raw.githubusercontent.com/kubernetes/ingress-nginx/nginx-0.30.0/deploy/static/provider/baremetal/service-nodeport.yaml >> $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	echo "$$INGRESS_SECRET" >> $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	# Add the certificates
	CERT=$$(cat $(DOCKER_DESKTOP_DIR)/localtest.me.crt | base64); \
	KEY=$$(cat $(DOCKER_DESKTOP_DIR)/localtest.me.key | base64); \
	sed -i '' "s/CERT/$$CERT/" $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml; \
	sed -i '' "s/KEY/$$KEY/" $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	lf=$$'\n'; \
	sed -i '' "/- \/nginx-ingress-controller/ s/$$/\\$$lf            - --default-ssl-certificate=\$$(POD_NAMESPACE)\/ssl-certificate/" deploy/docker-desktop/ingress-nginx.yaml
	# Change the service to LoadBalancer so the port is accessible at localhost
	sed -i '' "s/NodePort/LoadBalancer/" $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml

prepare-docker-desktop: $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml deploy-crds
	kubectl apply -f $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	kubectl apply -f $(DOCKER_DESKTOP_DIR)/docker-registry-pvc.yaml
	kubectl apply -f $(DOCKER_DESKTOP_DIR)/docker-registry.yaml

unprepare-docker-desktop:
	kubectl delete -f $(DOCKER_DESKTOP_DIR)/ingress-nginx.yaml
	kubectl delete -f $(DOCKER_DESKTOP_DIR)/docker-registry-pvc.yaml
	kubectl delete -f $(DOCKER_DESKTOP_DIR)/docker-registry.yaml

deploy-docker-desktop: prepare-docker-desktop
	# Directories needed for state and files
	mkdir -p db
	mkdir -p private
	mkdir -p shared
	cp -r templates db/
	# Template variables
	IP_ADDRESS=$$(ipconfig getifaddr en0); \
	export KARVDASH_INGRESS_DOMAIN=localtest.me; \
	export KARVDASH_IMAGE=$(KARVDASH_IMAGE_TAG); \
	export KARVDASH_DEBUG=1; \
	export KARVDASH_DASHBOARD_TITLE="Karvdash on Docker Desktop"; \
	export KARVDASH_DOCKER_REGISTRY="http://$$IP_ADDRESS:5000"; \
	export KARVDASH_DATASETS_AVAILABLE=""; \
	export KARVDASH_PERSISTENT_STORAGE_DIR="$(PWD)/db"; \
	export KARVDASH_PRIVATE_HOST_DIR="$(PWD)/private"; \
	export KARVDASH_SHARED_HOST_DIR="$(PWD)/shared"; \
	envsubst < $(DEPLOY_DIR)/karvdash.yaml | kubectl apply -f -

undeploy-docker-desktop: unprepare-docker-desktop undeploy

deploy-crds:
	kubectl apply -f $(DEPLOY_DIR)/argo-crd.yaml
	kubectl apply -f $(DEPLOY_DIR)/karvdash-crd.yaml

undeploy-crds:
	kubectl delete -f $(DEPLOY_DIR)/argo-crd.yaml
	kubectl delete -f $(DEPLOY_DIR)/karvdash-crd.yaml

deploy: deploy-crds
	# Check for necessary set variables
	if [[ -z $$KARVDASH_INGRESS_DOMAIN ]]; then echo "KARVDASH_INGRESS_DOMAIN is not set"; exit; fi; \
	if [[ -z $$KARVDASH_DOCKER_REGISTRY ]]; then echo "KARVDASH_DOCKER_REGISTRY is not set"; exit; fi; \
	if [[ -z $$KARVDASH_PERSISTENT_STORAGE_DIR ]]; then echo "KARVDASH_PERSISTENT_STORAGE_DIR is not set"; exit; fi; \
	if [[ -z $$KARVDASH_PRIVATE_HOST_DIR ]]; then echo "KARVDASH_PRIVATE_HOST_DIR is not set"; exit; fi; \
	if [[ -z $$KARVDASH_SHARED_HOST_DIR ]]; then echo "KARVDASH_SHARED_HOST_DIR is not set"; exit; fi; \
	export KARVDASH_IMAGE=$(KARVDASH_IMAGE_TAG); \
	export KARVDASH_DEBUG=""; \
	export KARVDASH_DASHBOARD_TITLE=$${KARVDASH_DASHBOARD_TITLE:="Karvdash"}; \
	export KARVDASH_DATASETS_AVAILABLE=$${KARVDASH_DATASETS_AVAILABLE:=""}; \
	envsubst < $(DEPLOY_DIR)/karvdash.yaml # | kubectl apply -f -

undeploy:
	kubectl delete -f $(DEPLOY_DIR)/karvdash.yaml

container:
	docker build -t $(KARVDASH_IMAGE_TAG) -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) .

push:
	docker push $(KARVDASH_IMAGE_TAG)
