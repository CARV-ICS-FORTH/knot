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
KUBECTL_VERSION?=v1.22.4

KNOT_VERSION=$(shell cat VERSION)
KNOT_IMAGE_TAG=$(REGISTRY_NAME)/knot:$(KNOT_VERSION)

CHART_DIR=./chart/knot

.PHONY: all check-ip-address deploy undeploy deploy-test undeploy-test delete-namespaces prepare-develop develop container container-push release

all: container

IP_ADDRESS?=$(shell ipconfig getifaddr en0 || ipconfig getifaddr en1 2> /dev/null)
INGRESS_URL=$(IP_ADDRESS).nip.io
DEVELOPMENT_URL=http://$(IP_ADDRESS):8000
HARBOR_ADMIN_PASSWORD=Harbor12345

define HELMFILE_DEPLOY_VALUES
--state-values-set storage.stateVolume.hostPath=$(PWD)/state \
--state-values-set storage.filesVolume.hostPath=$(PWD)/files \
--state-values-set harbor.adminPassword=$(HARBOR_ADMIN_PASSWORD) \
--state-values-set knot.developmentURL=$(DEVELOPMENT_URL) \
--state-values-set knot.localImage="true"
endef

check-ip-address:
ifeq ($(IP_ADDRESS),)
	$(error IP_ADDRESS is not set)
endif

deploy: check-ip-address
	mkdir -p state state/harbor
	mkdir -p files
	export KNOT_HOST="$(INGRESS_URL)"; \
	helmfile $(HELMFILE_DEPLOY_VALUES) sync

undeploy: check-ip-address
	export KNOT_HOST="$(INGRESS_URL)"; \
	helmfile $(HELMFILE_DEPLOY_VALUES) delete

deploy-test: check-ip-address
	export KNOT_HOST="$(INGRESS_URL)"; \
	helmfile --state-values-set knot.localImage="true" sync

undeploy-test: check-ip-address
	export KNOT_HOST="$(INGRESS_URL)"; \
	helmfile --state-values-set knot.localImage="true" destroy

delete-namespaces:
	kubectl delete namespace knot || true
	kubectl delete namespace nfs || true
	kubectl delete namespace csi-nfs || true
	kubectl delete namespace monitoring || true
	kubectl delete namespace harbor || true
	kubectl delete namespace argo || true
	kubectl delete namespace reflector || true
	kubectl delete namespace jupyterhub || true
	kubectl delete namespace ingress-nginx || true
	kubectl delete namespace cert-manager || true

prepare-develop:
	if [[ ! -d venv ]]; then python3 -m venv venv; fi
	source venv/bin/activate; \
	pip install --upgrade pip; \
	pip install -r requirements.txt;

develop: check-ip-address
	source venv/bin/activate; \
	export DJANGO_SECRET='%ad&%4*!xpf*$$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog'; \
	export DJANGO_DEBUG=1; \
	export KNOT_DATABASE_DIR=$(PWD)/state/knot; \
	export KNOT_VOUCH_URL="https://vouch.$(INGRESS_URL)"; \
	export KNOT_DASHBOARD_TITLE="Knot on Docker Desktop"; \
	export KNOT_INGRESS_URL="https://$(INGRESS_URL)"; \
	export KNOT_JUPYTERHUB_URL="https://jupyterhub.$(INGRESS_URL)"; \
	export KNOT_JUPYTERHUB_NOTEBOOK_DIR="notebooks"; \
	export KNOT_ARGO_WORKFLOWS_URL="https://argo.$(INGRESS_URL)"; \
	export KNOT_ARGO_WORKFLOWS_NAMESPACE="argo"; \
	export KNOT_HARBOR_URL="https://harbor.$(INGRESS_URL)"; \
	export KNOT_HARBOR_NAMESPACE="harbor"; \
	export KNOT_HARBOR_ADMIN_PASSWORD="$(HARBOR_ADMIN_PASSWORD)"; \
	export KNOT_GRAFANA_URL="https://grafana.$(INGRESS_URL)"; \
	export KNOT_GRAFANA_NAMESPACE="monitoring"; \
	kubectl port-forward -n knot deployment/knot 6379:6379 & \
	celery -A knot worker -l info & \
	./manage.py runserver 0.0.0.0:8000

container:
	docker build -f Dockerfile --build-arg TARGETARCH=amd64 --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KNOT_IMAGE_TAG) .

container-push:
	docker buildx build --platform linux/amd64,linux/arm64 --push -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) -t $(KNOT_IMAGE_TAG) .

release:
	if [[ -z "$${VERSION}" ]]; then echo "VERSION is not set"; exit 1; fi
	echo "$(VERSION)" > VERSION
	git add VERSION
	if [[ $(VERSION) =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$$ ]]; then \
		awk '/chart: knot\/knot/{print;getline;$$0="  version: $(VERSION:v%=%)"}1' helmfile.yaml > helmfile.yaml.tmp; \
		mv -f helmfile.yaml.tmp helmfile.yaml; \
		git add helmfile.yaml; \
	fi
	git commit -m "Bump version"
	git tag $(VERSION)
	# git push && git push --tags
