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

DEPLOY_DIR=deploy
CHART_DIR=./chart/karvdash

.PHONY: all deploy-requirements undeploy-requirements deploy-crds undeploy-crds deploy-local undeploy-local prepare-develop service-containers service-containers-push container container-push release

all: container

IP_ADDRESS=$(shell ipconfig getifaddr en0 || ipconfig getifaddr en1)

INGRESS_URL=${IP_ADDRESS}.nip.io
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
  commonName: ${INGRESS_URL}
  dnsNames:
  - "${INGRESS_URL}"
  - "*.${INGRESS_URL}"
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
	helm repo add argo https://argoproj.github.io/argo-helm
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
	kubectl wait --for condition=Available -n cert-manager deployment/cert-manager-webhook; \
	echo "$$INGRESS_CERTIFICATE" | kubectl apply -n ingress-nginx -f -
	helm list --namespace ingress-nginx -q | grep ingress || \
	helm install ingress ingress-nginx/ingress-nginx --version 3.19.0 --namespace ingress-nginx \
	--set controller.extraArgs.default-ssl-certificate=ingress-nginx/ssl-certificate \
	--set controller.admissionWebhooks.enabled=false
	# Deploy argo (will start when OAuth secret is created)
	kubectl create namespace argo || true
	kubectl get configmap ssl-certificate -n argo || \
	kubectl -n ingress-nginx wait --for condition=Ready certificate/ssl-certificate; \
	kubectl create configmap ssl-certificate -n argo --from-literal="ca.crt=`kubectl get secret -n ingress-nginx ssl-certificate -o 'go-template={{index .data \"ca.crt\" | base64decode }}'`"
	helm list --namespace argo -q | grep argo || \
	helm install argo argo/argo-workflows --version 0.2.12 --namespace argo \
	--set controller.image.tag=v3.1.1 \
	--set controller.containerRuntimeExecutor=k8sapi \
	--set executor.image.tag=v3.1.1 \
	--set server.image.tag=v3.1.1 \
	--set server.extraArgs\[0\]="--auth-mode=sso" \
	--set server.volumeMounts\[0\].name="ssl-certificate-volume" \
	--set server.volumeMounts\[0\].mountPath="/etc/ssl/certs/${INGRESS_URL}.crt" \
	--set server.volumeMounts\[0\].subPath="ca.crt" \
	--set server.volumes\[0\].name="ssl-certificate-volume" \
	--set server.volumes\[0\].configMap.name="ssl-certificate" \
	--set server.ingress.enabled=true \
	--set server.ingress.hosts\[0\]=argo.${INGRESS_URL} \
	--set server.sso.issuer=https://${INGRESS_URL}/oauth \
	--set server.sso.clientId.name=karvdash-oauth-argo \
	--set server.sso.clientId.key=client-id \
	--set server.sso.clientSecret.name=karvdash-oauth-argo \
	--set server.sso.clientSecret.key=client-secret \
	--set server.sso.redirectUrl=https://argo.${INGRESS_URL}/oauth2/callback \
	--set server.sso.rbac.enabled=true
	# Deploy DLF
	# kubectl apply -f https://raw.githubusercontent.com/datashim-io/datashim/master/release-tools/manifests/dlf.yaml
	# kubectl wait --timeout=600s --for=condition=ready pods -l app.kubernetes.io/name=dlf -n dlf

undeploy-requirements:
	# Remove DLF
	# kubectl delete -f https://raw.githubusercontent.com/datashim-io/datashim/master/release-tools/manifests/dlf.yaml || true
	# Remove argo
	helm uninstall argo --namespace argo || true
	kubectl delete configmap ssl-certificate -n argo || true
	kubectl delete namespace argo || true
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

deploy-local:
	# Create necessary directories
	mkdir -p db
	mkdir -p files
	helm list -q | grep karvdash || \
	helm install karvdash $(CHART_DIR) --namespace default \
	--set image="$(KARVDASH_IMAGE_TAG)" \
	--set karvdash.djangoSecret='%ad&%4*!xpf*$$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog' \
	--set karvdash.djangoDebug="1" \
	--set karvdash.dashboardTitle="Karvdash on Docker Desktop" \
	--set karvdash.ingressURL="https://${INGRESS_URL}" \
	--set karvdash.registryURL="http://${IP_ADDRESS}:5000" \
	--set karvdash.stateHostPath="$(PWD)/db" \
	--set karvdash.filesURL="file://$(PWD)/files" \
	--set karvdash.argoURL="https://argo.${INGRESS_URL}" \
	--set karvdash.argoNamespace="argo"

undeploy-local:
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
	# git push && git push --tags
