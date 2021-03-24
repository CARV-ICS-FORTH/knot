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

LOCAL_S3_DATASET_TEMPLATE = '''
apiVersion: com.ie.ibm.hpsys/v1alpha1
kind: Dataset
metadata:
  name: $NAME
spec:
  local:
    type: "COS"
    endpoint: "http://${MINIO}.${NAMESPACE}.svc:9000"
    accessKeyID: $ACCESSKEYID
    secretAccessKey: $SECRETACCESSKEY
    bucket: $BUCKET
    region: ""
---
kind: Template
name: S3 (local)
description: Dataset for running Minio service
variables:
- name: NAMESPACE
  default: default
- name: NAME
  default: dataset
- name: MINIO
  label: Minio Service Name
  default: ""
  help: In current namespace and listening at port 9000
- name: ACCESSKEYID
  label: Access Key ID
  default: ""
- name: SECRETACCESSKEY
  label: Secret Access Key
  default: ""
- name: BUCKET
  default: ""
'''

REMOTE_S3_DATASET_TEMPLATE = '''
apiVersion: com.ie.ibm.hpsys/v1alpha1
kind: Dataset
metadata:
  name: $NAME
spec:
  local:
    type: "COS"
    endpoint: $ENDPOINT
    accessKeyID: $ACCESSKEYID
    secretAccessKey: $SECRETACCESSKEY
    bucket: $BUCKET
    region: $REGION
---
kind: Template
name: S3 (remote)
description: Dataset for remote S3 endpoint
variables:
- name: NAME
  default: dataset
- name: ENDPOINT
  default: "https://s3.amazonaws.com"
  help: S3 service endpoint URL
- name: ACCESSKEYID
  label: Access Key ID
  default: ""
- name: SECRETACCESSKEY
  label: Secret Access Key
  default: ""
- name: BUCKET
  default: ""
- name: REGION
  default: ""
  help: Optional
'''

SECRET_S3_SECRET_TEMPLATE = '''
apiVersion: v1
kind: Secret
metadata:
  name: $NAME
stringData:
  accessKeyID: $ACCESSKEYID
  secretAccessKey: $SECRETACCESSKEY
---
kind: Template
name: S3 secret
description: Secret for remote S3 endpoint
variables:
- name: NAME
  default: secret
- name: ACCESSKEYID
  label: Access Key ID
  default: ""
- name: SECRETACCESSKEY
  label: Secret Access Key
  default: ""
'''

SECRET_S3_DATASET_TEMPLATE = '''
apiVersion: com.ie.ibm.hpsys/v1alpha1
kind: Dataset
metadata:
  name: $NAME
spec:
  local:
    type: "COS"
    endpoint: $ENDPOINT
    secret-name: $SECRETNAME
    bucket: $BUCKET
    region: $REGION
---
kind: Template
name: S3 (secret)
description: Dataset for remote S3 endpoint with predefined secret
variables:
- name: NAME
  default: dataset
- name: ENDPOINT
  default: "https://s3.amazonaws.com"
  help: S3 service endpoint URL
- name: SECRETNAME
  label: Secret Containing the Access Key ID and Secret Access Key
  default: ""
- name: BUCKET
  default: ""
- name: REGION
  default: ""
  help: Optional
'''

LOCAL_H3_DATASET_TEMPLATE = '''
apiVersion: com.ie.ibm.hpsys/v1alpha1
kind: Dataset
metadata:
  name: $NAME
spec:
  local:
    type: "H3"
    storageUri: "redis://${REDIS}.${NAMESPACE}.svc"
    bucket: $BUCKET
---
kind: Template
name: H3 (local)
description: Dataset for H3 over running Redis-compatible service
variables:
- name: NAMESPACE
  default: default
- name: NAME
  default: dataset
- name: REDIS
  label: Redis-compatible Service Name
  default: ""
  help: In current namespace and listening at port 6379
- name: BUCKET
  default: ""
'''

REMOTE_H3_DATASET_TEMPLATE = '''
apiVersion: com.ie.ibm.hpsys/v1alpha1
kind: Dataset
metadata:
  name: $NAME
spec:
  local:
    type: "H3"
    storageUri: $STORAGEURI
    bucket: $BUCKET
---
kind: Template
name: H3 (remote)
description: Dataset for H3 over remote key-value service
variables:
- name: NAME
  default: dataset
- name: STORAGEURI
  label: H3 Storage URI
  default: "redis://example.com"
- name: BUCKET
  default: ""
'''

ARCHIVE_DATASET_TEMPLATE = '''
apiVersion: com.ie.ibm.hpsys/v1alpha1
kind: Dataset
metadata:
  name: $NAME
spec:
  local:
    type: "ARCHIVE"
    url: $URL
    format: "application/x-tar"
---
kind: Template
name: Archive
description: Dataset for remote archive
variables:
- name: NAME
  default: dataset
- name: URL
  label: Archive URL
  default: "http://example.com/archive.tar.gz"
'''

# HOSTPATH_DATASET_TEMPLATE = '''
# apiVersion: com.ie.ibm.hpsys/v1alpha1
# kind: Dataset
# metadata:
#   name: $NAME
# spec:
#   local:
#     type: "HOST"
#     path: $ENDPOINT
#     hostPathType: Directory
# ---
# kind: Template
# name: HostPath
# description: Dataset for local host path
# variables:
# - name: NAME
#   default: dataset
# - name: ENDPOINT
#   default: "/tmp"
#   help: Existing local host path
# '''
