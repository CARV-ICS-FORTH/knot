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

.PHONY: all container

all: container push

container:
	docker build -t $(IMAGE_TAG) -f Dockerfile --build-arg KUBECTL_VERSION=$(KUBECTL_VERSION) .

push:
	docker push $(IMAGE_TAG)
	docker tag $(IMAGE_TAG) $(REGISTRY_NAME)/$(IMAGE_NAME):latest
	docker push $(REGISTRY_NAME)/$(IMAGE_NAME):latest
