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

MINIKUBE?=no
BAREMETAL?=no
DEVELOPMENT?=no

REGISTRY_NAME?=carvicsforth
KUBECTL_VERSION?=v1.22.4

KARVDASH_VERSION=$(shell cat VERSION)
KARVDASH_IMAGE_TAG=$(REGISTRY_NAME)/karvdash:$(KARVDASH_VERSION)

CHART_DIR=./chart/karvdash

.PHONY: all deploy-requirements undeploy-requirements deploy-local undeploy-local prepare-develop develop container container-push release

all: container

ifeq (${MINIKUBE}, yes)
IP_ADDRESS=$(shell minikube ip)
HELMFILE_ENV=minikube
else ifneq (${BAREMETAL}, yes)
IP_ADDRESS=$(shell ipconfig getifaddr en0 || ipconfig getifaddr en1)
HELMFILE_ENV=default
else
ifndef IP_ADDRESS
$(error IP_ADDRESS is not set)
endif
HELMFILE_ENV=baremetal
endif

ifneq (${DEVELOPMENT}, yes)
DEVELOPMENT_URL=
else
DEVELOPMENT_URL=http://${IP_ADDRESS}:8000
endif

INGRESS_URL=${IP_ADDRESS}.nip.io
HARBOR_ADMIN_PASSWORD=Harbor12345

deploy-requirements:
	export IP_ADDRESS="${IP_ADDRESS}"; \
	helmfile -e ${HELMFILE_ENV} sync
	# Deploy DLF
	# kubectl apply -f https://raw.githubusercontent.com/datashim-io/datashim/master/release-tools/manifests/dlf.yaml
	# kubectl wait --timeout=600s --for=condition=ready pods -l app.kubernetes.io/name=dlf -n dlf

undeploy-requirements:
	# Remove DLF
	# kubectl delete -f https://raw.githubusercontent.com/datashim-io/datashim/master/release-tools/manifests/dlf.yaml || true
	export IP_ADDRESS="${IP_ADDRESS}"; \
	helmfile -e ${HELMFILE_ENV} delete
	# Remove namespaces
	kubectl delete namespace openbio || true
	kubectl delete namespace monitoring || true
	kubectl delete namespace harbor || true
	kubectl delete namespace argo || true
	kubectl delete namespace reflector || true
	kubectl delete namespace jupyterhub || true
	kubectl delete namespace ingress-nginx || true
	kubectl delete namespace cert-manager || true

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
	--set karvdash.certificateSecretName="ssl-certificate" \
	--set karvdash.certificateSecretKey="ca.crt" \
	--set karvdash.stateHostPath="$(PWD)/db" \
	--set karvdash.filesURL="file://$(PWD)/files" \
	--set karvdash.developmentURL="${DEVELOPMENT_URL}" \
	--set karvdash.jupyterHubURL="https://jupyterhub.${INGRESS_URL}" \
	--set karvdash.jupyterHubNamespace="jupyterhub" \
	--set karvdash.jupyterHubNotebookDir="notebooks" \
	--set karvdash.argoWorkflowsURL="https://argo.${INGRESS_URL}" \
	--set karvdash.argoWorkflowsNamespace="argo" \
	--set karvdash.harborURL="https://harbor.${INGRESS_URL}" \
	--set karvdash.harborNamespace="harbor" \
	--set karvdash.harborAdminPassword="${HARBOR_ADMIN_PASSWORD}" \
	--set karvdash.grafanaURL="https://grafana.${INGRESS_URL}" \
	--set karvdash.grafanaNamespace="monitoring" \
	--set karvdash.openBioURL="https://openbio.${INGRESS_URL}" \
	--set karvdash.openBioNamespace="openbio"

undeploy-local:
	helm uninstall karvdash --namespace default

prepare-develop:
	# Create necessary directories
	mkdir -p db
	mkdir -p files
	# Create the Python environment and prepare the application
	if [[ ! -d venv ]]; then python3 -m venv venv; fi
	source venv/bin/activate; \
	pip install -r requirements.txt; \
	./manage.py migrate; \
	./manage.py createadmin --noinput --username admin --password admin --email admin@example.com --preserve

develop:
	source venv/bin/activate; \
	export DJANGO_SECRET='%ad&%4*!xpf*$$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog'; \
	export DJANGO_DEBUG=1; \
	export KARVDASH_VOUCH_URL="https://vouch.${INGRESS_URL}"; \
	export KARVDASH_DASHBOARD_TITLE="Karvdash on Docker Desktop"; \
	export KARVDASH_INGRESS_URL="https://${INGRESS_URL}"; \
	export KARVDASH_JUPYTERHUB_URL="https://jupyterhub.${INGRESS_URL}"; \
	export KARVDASH_JUPYTERHUB_NOTEBOOK_DIR="notebooks"; \
	export KARVDASH_ARGO_WORKFLOWS_URL="https://argo.${INGRESS_URL}"; \
	export KARVDASH_ARGO_WORKFLOWS_NAMESPACE="argo"; \
	export KARVDASH_HARBOR_URL="https://harbor.${INGRESS_URL}"; \
	export KARVDASH_HARBOR_NAMESPACE="harbor"; \
	export KARVDASH_HARBOR_ADMIN_PASSWORD="${HARBOR_ADMIN_PASSWORD}"; \
	export KARVDASH_GRAFANA_URL="https://grafana.${INGRESS_URL}"; \
	export KARVDASH_GRAFANA_NAMESPACE="monitoring"; \
	export KARVDASH_OPENBIO_URL="https://openbio.${INGRESS_URL}"; \
	export KARVDASH_OPENBIO_NAMESPACE="openbio"; \
	kubectl port-forward deployment/karvdash 6379:6379 & \
	celery -A karvdash worker -l info & \
	./manage.py runserver 0.0.0.0:8000

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
