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

CHART_DIR=./chart/karvdash

.PHONY: all deploy-requirements undeploy-requirements deploy-crds undeploy-crds deploy-local undeploy-local prepare-develop container container-push release

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

JUPYTERHUB_CLIENT_ID=56kSn87XXbk4GuFBQ7zQrXcVQNyyMWKb1vR2diUZ
JUPYTERHUB_CLIENT_SECRET=FvxWxBTbhgQbo1sGbc6yLsza0Vwo6jZQBpiOSDYcghCjWWcpRzBygzJSQ8M4CunflPn9pCOr25vVnGr0N2ytR6FjklSesc28BqkHSM6aVIYA5RKFZaOpiMj9Ghc5VDfN
define JUPYTERHUB_CONFIG
c.ConfigurableHTTPProxy.api_url = "http://proxy-api.jupyterhub.svc:8001"
c.JupyterHub.hub_connect_url = "http://hub.jupyterhub.svc:8081"
c.KubeSpawner.enable_user_namespaces = True
c.KubeSpawner.user_namespace_template = "karvdash-{username}"
c.KubeSpawner.notebook_dir = "/private/notebooks"
endef

export INGRESS_CERTIFICATE
export JUPYTERHUB_CONFIG
deploy-requirements:
	if [[ `helm version --short` != v3* ]]; then echo "Can not find Helm 3 installed"; exit 1; fi
	helm repo add twuni https://helm.twun.io
	helm repo add jetstack https://charts.jetstack.io
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
	helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
	helm repo add argo https://argoproj.github.io/argo-helm
	helm repo update
	# Deploy Docker Registry
	kubectl create namespace registry || true
	helm list --namespace registry -q | grep registry || \
	helm install registry twuni/docker-registry --version 1.10.0 --namespace registry \
	--set persistence.enabled=true \
	--set persistence.deleteEnabled=true \
	--set service.type=LoadBalancer
	# Deploy cert-manager
	kubectl create namespace cert-manager || true
	helm list --namespace cert-manager -q | grep cert-manager || \
	helm install cert-manager cert-manager/cert-manager --version v1.1.0 --namespace cert-manager \
	--set installCRDs=true
	# Deploy NGINX Ingress Controller
	kubectl create namespace ingress-nginx || true
	kubectl get secret ssl-certificate -n ingress-nginx || \
	for i in $$(seq 1 5); do echo "$$INGRESS_CERTIFICATE" | kubectl apply -n ingress-nginx -f - && break || sleep 5; done
	helm list --namespace ingress-nginx -q | grep ingress || \
	helm install ingress ingress-nginx/ingress-nginx --version 3.19.0 --namespace ingress-nginx \
	--set controller.extraArgs.default-ssl-certificate=ingress-nginx/ssl-certificate \
	--set controller.admissionWebhooks.enabled=false
	# Deploy JupyterHub
	kubectl create namespace jupyterhub || true
	kubectl get secret karvdash-oauth-jupyterhub -n jupyterhub || \
	kubectl create secret generic karvdash-oauth-jupyterhub -n jupyterhub --from-literal=client-id=${JUPYTERHUB_CLIENT_ID} --from-literal=client-secret=${JUPYTERHUB_CLIENT_SECRET}
	helm list --namespace jupyterhub -q | grep jupyterhub || \
	helm install jupyterhub jupyterhub/jupyterhub --version=1.0.1 --namespace jupyterhub \
	--set hub.config.JupyterHub.authenticator_class=generic-oauth \
	--set hub.config.Authenticator.auto_login="true" \
	--set hub.config.GenericOAuthenticator.client_id=${JUPYTERHUB_CLIENT_ID} \
	--set hub.config.GenericOAuthenticator.client_secret=${JUPYTERHUB_CLIENT_SECRET} \
	--set hub.config.GenericOAuthenticator.tls_verify="false" \
	--set hub.config.GenericOAuthenticator.oauth_callback_url=https://jupyterhub.${INGRESS_URL}/hub/oauth_callback \
	--set hub.config.GenericOAuthenticator.authorize_url=https://${INGRESS_URL}/oauth/authorize/ \
	--set hub.config.GenericOAuthenticator.token_url=https://${INGRESS_URL}/oauth/token/ \
	--set hub.config.GenericOAuthenticator.userdata_url=https://${INGRESS_URL}/oauth/userinfo/ \
	--set hub.config.GenericOAuthenticator.scope\[0\]=openid \
	--set hub.config.GenericOAuthenticator.scope\[1\]=profile \
	--set hub.config.GenericOAuthenticator.scope\[2\]=email \
	--set hub.config.GenericOAuthenticator.username_key=preferred_username \
	--set hub.extraConfig."myConfig\.py"="$$JUPYTERHUB_CONFIG" \
	--set hub.networkPolicy.enabled="false" \
	--set proxy.service.type=ClusterIP \
	--set proxy.chp.networkPolicy.enabled="false" \
	--set singleuser.networkPolicy.enabled="false" \
	--set singleuser.storage.type=none \
	--set prePuller.hook.enabled=false \
	--set prePuller.continuous.enabled=false \
	--set scheduling.userScheduler.enabled=false \
	--set ingress.enabled=true \
	--set ingress.hosts\[0\]=jupyterhub.${INGRESS_URL}
	# Deploy Argo Workflows
	kubectl create namespace argo || true
	kubectl get configmap ssl-certificate -n argo || \
	kubectl -n ingress-nginx wait --for condition=Ready certificate/ssl-certificate; \
	kubectl create configmap ssl-certificate -n argo --from-literal="ca.crt=`kubectl get secret ssl-certificate -n ingress-nginx -o 'go-template={{index .data \"ca.crt\" | base64decode }}'`"
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
	# Remove Argo Workflows
	helm uninstall argo --namespace argo || true
	kubectl delete namespace argo || true
	# Remove JupyterHub
	helm uninstall jupyterhub --namespace jupyterhub || true
	kubectl delete namespace jupyterhub || true
	# Remove NGINX Ingress Controller
	helm uninstall ingress --namespace ingress-nginx || true
	kubectl delete namespace ingress-nginx || true
	# Remove cert-manager
	helm uninstall cert-manager --namespace cert-manager || true
	kubectl delete namespace cert-manager || true
	# Remove Docker Registry
	helm uninstall registry --namespace registry || true
	kubectl delete namespace registry || true

deploy-crds:
	kubectl apply -f $(CHART_DIR)/crds/karvdash-crd.yaml

undeploy-crds:
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
	--set karvdash.jupyterHubURL="https://jupyterhub.${INGRESS_URL}" \
	--set karvdash.jupyterHubNamespace="jupyterhub" \
	--set karvdash.jupyterHubNotebookDir="notebooks" \
	--set karvdash.argoWorkflowsURL="https://argo.${INGRESS_URL}" \
	--set karvdash.argoWorkflowsNamespace="argo"

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
