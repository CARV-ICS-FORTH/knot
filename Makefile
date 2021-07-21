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
ZEPPELIN_VERSION=0.9.0.7
ZEPPELIN_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin:$(ZEPPELIN_VERSION)
ZEPPELIN_GPU_IMAGE_TAG=$(REGISTRY_NAME)/karvdash-zeppelin-gpu:$(ZEPPELIN_VERSION)

DEPLOY_DIR=deploy
CHART_DIR=./chart/karvdash

.PHONY: all deploy-requirements undeploy-requirements deploy-crds undeploy-crds deploy-local undeploy-local prepare-develop service-containers service-containers-push container container-push release

all: container

IP_ADDRESS=$(shell ipconfig getifaddr en0 || ipconfig getifaddr en1)

INGRESS_EXTERNAL_ADDRESS=${IP_ADDRESS}.nip.io
define INGRESS_CERTIFICATE
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: selfsigned
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ssl-certificate
spec:
  secretName: ssl-certificate
  duration: 87600h
  commonName: ${INGRESS_EXTERNAL_ADDRESS}
  dnsNames:
  - "${INGRESS_EXTERNAL_ADDRESS}"
  - "*.${INGRESS_EXTERNAL_ADDRESS}"
  privateKey:
    algorithm: RSA
    size: 2048
  issuerRef:
    name: selfsigned
endef

export INGRESS_CERTIFICATE
deploy-requirements:
	if [[ `helm version --short` != v3* ]]; then echo "Can not find Helm 3 installed"; exit 1; fi
	helm repo add twuni https://helm.twun.io
	helm repo add jetstack https://charts.jetstack.io
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
	helm repo update
	# Deploy registry
	kubectl create namespace registry || true
	helm list --namespace registry -q | grep registry || \
	helm install registry twuni/docker-registry --version 1.10.0 --namespace registry \
	--set persistence.enabled=true \
	--set persistence.deleteEnabled=true \
	--set service.type=LoadBalancer
	# Deploy cert-manager
	kubectl create namespace cert-manager || true
	helm list --namespace cert-manager -q | grep cert-manager || \
	helm install cert-manager jetstack/cert-manager --version v1.1.0 --namespace cert-manager \
	--set installCRDs=true
	# Deploy ingress
	kubectl create namespace ingress-nginx || true
	kubectl get secret ssl-certificate -n ingress-nginx || \
	echo "$$INGRESS_CERTIFICATE" | kubectl apply -n ingress-nginx -f -
	helm list --namespace ingress-nginx -q | grep ingress || \
	helm install ingress ingress-nginx/ingress-nginx --version 3.19.0 --namespace ingress-nginx \
	--set controller.extraArgs.default-ssl-certificate=ingress-nginx/ssl-certificate \
	--set controller.admissionWebhooks.enabled=false
	# Deploy DLF
	# kubectl apply -f https://raw.githubusercontent.com/datashim-io/datashim/master/release-tools/manifests/dlf.yaml
	# kubectl wait --timeout=600s --for=condition=ready pods -l app.kubernetes.io/name=dlf -n dlf

undeploy-requirements:
	# Remove DLF
	# kubectl delete -f https://raw.githubusercontent.com/datashim-io/datashim/master/release-tools/manifests/dlf.yaml || true
	# Remove ingress
	helm uninstall ingress --namespace ingress-nginx || true
	kubectl delete secret ssl-certificate -n ingress-nginx || true
	kubectl delete namespace ingress-nginx || true
	# Remove cert-manager
	helm uninstall cert-manager --namespace cert-manager || true
	kubectl delete namespace cert-manager || true
	# Remove registry
	helm uninstall registry --namespace registry || true
	kubectl delete namespace registry || true

deploy-crds:
	kubectl apply -f $(CHART_DIR)/crds/karvdash-crd.yaml
	kubectl apply -f $(CHART_DIR)/crds/argo-crd.yaml

undeploy-crds:
	kubectl delete -f $(CHART_DIR)/crds/argo-crd.yaml
	kubectl delete -f $(CHART_DIR)/crds/karvdash-crd.yaml

deploy-local: deploy-requirements
	# Create necessary directories
	mkdir -p db
	mkdir -p files
	helm list -q | grep karvdash || \
	helm install karvdash $(CHART_DIR) --namespace default \
	--set image="$(KARVDASH_IMAGE_TAG)" \
	--set karvdash.djangoSecret='%ad&%4*!xpf*$$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog' \
	--set karvdash.djangoDebug="1" \
	--set karvdash.dashboardTitle="Karvdash on Docker Desktop" \
	--set karvdash.ingressURL="https://${IP_ADDRESS}.nip.io" \
	--set karvdash.dockerRegistryURL="http://${IP_ADDRESS}:5000" \
	--set karvdash.datasetsAvailable="0" \
	--set karvdash.stateHostPath="$(PWD)/db" \
	--set karvdash.filesURL="file://$(PWD)/files"

undeploy-local: undeploy-requirements undeploy-crds
	helm uninstall karvdash --namespace default

prepare-develop: deploy-crds
	# Create necessary directories
	mkdir -p db
	mkdir -p files
	# Create the Python environment and prepare the application
	if [[ ! -d venv ]]; then python3 -m venv venv; fi
	if [[ -z "$${VIRTUAL_ENV}" ]]; then \
		source venv/bin/activate; \
		pip install -r requirements.txt; \
		./manage.py migrate; \
		./manage.py createadmin --noinput --username admin --password admin --email admin@example.com --preserve; \
	fi

service-containers:
	docker build -f containers/zeppelin/Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(ZEPPELIN_IMAGE_TAG) .
	docker build -f containers/zeppelin-gpu/Dockerfile --build-arg BASE=$(ZEPPELIN_IMAGE_TAG) -t $(ZEPPELIN_GPU_IMAGE_TAG) .

service-containers-push: service-containers
	docker push $(ZEPPELIN_IMAGE_TAG)
	docker push $(ZEPPELIN_GPU_IMAGE_TAG)

container:
	docker build -f Dockerfile --build-arg TARGETARCH=amd64 --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KARVDASH_IMAGE_TAG) .

container-push:
	docker buildx build --platform linux/amd64,linux/arm64 --push -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KARVDASH_IMAGE_TAG) .

release:
	if [[ -z "$${VERSION}" ]]; then echo "VERSION is not set"; exit 1; fi
	echo "${VERSION}" > VERSION
	git add VERSION
	git commit -m "Bump version"
	git tag ${VERSION}
	# make container && make container-push
	# make service-containers && make service-containers-push
	# git push && git push --tags
