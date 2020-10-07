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

VERSION=$(shell cat VERSION)
KUBECTL_VERSION=v1.15.10
REGISTRY_NAME=carvicsforth
IMAGE_NAME=karvdash
IMAGE_TAG=$(REGISTRY_NAME)/$(IMAGE_NAME):$(VERSION)

CERTS_DIR=deploy/docker-desktop

.PHONY: all container

all: container push

$(CERTS_DIR)/localtest.me.key $(CERTS_DIR)/localtest.me.crt:
	mkdir -p $(CERTS_DIR)
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $(CERTS_DIR)/localtest.me.key -out $(CERTS_DIR)/localtest.me.crt -subj "/CN=*.localtest.me/CN=localtest.me/O=localtest.me"
	CERT="  tls.crt: "`cat $(CERTS_DIR)/localtest.me.crt | base64`
	KEY="  tls.key: "`cat $(CERTS_DIR)/localtest.me.key | base64`
	echo $(CERT) $(KEY)

prepare-docker-desktop: $(CERTS_DIR)/localtest.me.key $(CERTS_DIR)/localtest.me.crt
	echo "asdf"

container:
	docker build -t $(IMAGE_TAG) -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) .

push:
	docker push $(IMAGE_TAG)
