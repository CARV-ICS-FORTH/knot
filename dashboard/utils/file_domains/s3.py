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

import os
import zipfile
import boto3
import botocore
import secrets
import string
import tempfile
import json
import yaml

from urllib.parse import urlparse

from ..kubernetes import KubernetesClient
from ..template import Template
from ...datasets import SECRET_S3_SECRET_TEMPLATE, SECRET_S3_DATASET_TEMPLATE


class S3DomainPathWorker(object):
    def __init__(self, domain, path_components):
        self._domain = domain
        self._path_components = path_components

    @property
    def real_path(self):
        return '' if not self._path_components else '/'.join(self._path_components)

    def exists(self, name=None):
        if self.isfile(name) or self.isdir(name):
            return True

        return False

    def isfile(self, name=None):
        name = os.path.join(self.real_path, name or '').rstrip('/')
        if not name:
            return False

        try:
            self._domain.bucket.Object(name).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                pass
            else:
                raise
        else:
            return True

        return False

    def isdir(self, name=None):
        name = os.path.join(self.real_path, name or '').rstrip('/')
        if not name:
            return True

        try:
            self._domain.bucket.Object(name + '/').load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                pass
            else:
                raise
        else:
            return True

        # This may be a common prefix, acting as a folder.
        dir_path = name + '/'
        count = len(list(self._domain.bucket.objects.filter(Prefix=dir_path, MaxKeys=10)))
        if count:
            return True

        return False

    def open(self, name, mode):
        name = os.path.join(self.real_path, name).rstrip('/')
        return self._domain.bucket.Object(name).get()['Body']

    def listdir(self):
        dirs = set()
        listing = []
        dir_path = '' if not self.real_path else self.real_path + '/'
        client = self._domain.bucket.meta.client
        paginator = client.get_paginator('list_objects')
        for page in paginator.paginate(Bucket=self._domain.bucket.name, Prefix=dir_path, Delimiter='/'):
            for prefix in page.get('CommonPrefixes', []):
                name = prefix.get('Prefix')
                if name in dirs:
                    continue
                dirs.add(name)
                listing.append({'name': name[len(dir_path):].rstrip('/'),
                                'modified': None,
                                'type': 'dir',
                                'size': 0})
            for o in page.get('Contents', []):
                listing.append({'name': o['Key'][len(dir_path):],
                                'modified': o['LastModified'],
                                'type': 'file',
                                'size': o['Size']})
        return listing

    def mkdir(self, name):
        dir_path = os.path.join(self.real_path, name).rstrip('/') + '/'
        self._domain.bucket.Object(dir_path).put()

    def rmdir(self, name):
        dir_path = os.path.join(self.real_path, name).rstrip('/') + '/'
        count = len(list(self._domain.bucket.objects.filter(Prefix=dir_path, MaxKeys=10)))
        if count:
            raise ValueError('Directory not empty')
        self._domain.bucket.Object(dir_path).delete()

        # Fix for MinIO which merges dirs into single objects.
        if not self.isdir():
            self.mkdir('')

    def upload(self, files):
        for f in files:
            name = os.path.join(self.real_path, f.name).rstrip('/')
            self._domain.bucket.Object(name).put(Body=f)

    def download(self, name, response):
        zip_path = os.path.join(self.real_path, name).rstrip('/') + '/'
        with zipfile.ZipFile(response, 'w') as zip_file:
            client = self._domain.bucket.meta.client
            paginator = client.get_paginator('list_objects')
            for page in paginator.paginate(Bucket=self._domain.bucket.name, Prefix=zip_path):
                for o in page.get('Contents', []):
                    zip_file.writestr(o['Key'][len(zip_path):], self._domain.bucket.Object(o['Key']).get()['Body'].read())

    def remove(self, name):
        name = os.path.join(self.real_path, name).rstrip('/')
        self._domain.bucket.Object(name).delete()

class S3Domain(object):
    def __init__(self, url, mount_dir, user):
        if not user:
            raise ValueError('Empty user')

        self._url = urlparse(url)
        if self._url.scheme not in ('minio', 'minios', 'aws'):
            raise ValueError('Unsupported S3 domain URL')
        self._user = user

        self._bucket_prefix = self._url.path.lstrip('/').rstrip('-') or 'karvdash'

        # Start an S3 session.
        configuration = {'aws_access_key_id': self._url.username,
                         'aws_secret_access_key': self._url.password}
        if self._url.scheme in ('minio', 'minios'):
            configuration['endpoint_url'] = '%s://%s:%s' % ('http' if self._url.scheme == 'minio' else 'https',
                                                            self._url.hostname,
                                                            self._url.port)
            configuration['config'] = botocore.client.Config(signature_version='s3v4')
        elif self._url.scheme == 'aws':
            configuration['region_name'] = self._url.hostname
        self._s3 = boto3.resource('s3', **configuration)
        self._bucket = self._s3.Bucket(self.bucket_name)
        self.create_bucket() # Creates bucket and secret.

        # Create dataset.
        kubernetes_client = KubernetesClient()
        for dataset in kubernetes_client.list_crds(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self._user.namespace, plural='datasets'):
            try:
                if self.volume_name == dataset['metadata']['name']:
                    return
            except:
                continue

        template = Template(SECRET_S3_DATASET_TEMPLATE)
        template.NAME = self.volume_name
        template.ENDPOINT = '%s://%s:%s' % ('http' if self._url.scheme == 'minio' else 'https', self._url.hostname, self._url.port)
        template.SECRETNAME = 'karvdash-minio'
        template.BUCKET = self.bucket_name
        template.REGION = '""'

        template_yaml = yaml.load(template.yaml, Loader=yaml.FullLoader)
        if 'labels' not in template_yaml['metadata']:
            template_yaml['metadata']['labels'] = {}
        template_yaml['metadata']['labels']['karvdash-hidden'] = 'true'

        # try:
        #     kubernetes_client.delete_crd(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self._user.namespace, plural='datasets', name=self.volume_name)
        # except:
        #     pass
        kubernetes_client.apply_crd(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self._user.namespace, plural='datasets', yaml=template_yaml)

    def create_bucket(self):
        # Create bucket if it does not exist.
        if not self._bucket.creation_date:
            self._s3.create_bucket(Bucket=self.bucket_name)

    @property
    def bucket(self):
        return self._bucket

    @property
    def name(self):
        ''' How to name the domain when mounting it ("private" or "shared"). '''
        raise NotImplementedError

    @property
    def volume_name(self):
        ''' How to name the volume when mounting it. '''
        return 'karvdash-%s-volume-%s' % (self._user, self.name)

    @property
    def mount_dir(self):
        ''' Where to mount the domain. '''
        return '/%s' % self.name

    @property
    def bucket_name(self):
        ''' The user-specific bucket for the domain (for internal use). '''
        raise NotImplementedError

    @property
    def url(self):
        ''' The URL of the domain to be mounted. '''
        return 's3://%s/%s' % (self._url.netloc, self.bucket_name)

    def path_worker(self, subpath_components):
        return S3DomainPathWorker(self, subpath_components)

class PrivateS3Domain(S3Domain):
    def create_bucket(self):
        # Create bucket and secret if either does not exist and apply policy.
        secret_exists = False
        kubernetes_client = KubernetesClient()
        for secret in kubernetes_client.list_secrets(namespace=self._user.namespace):
            name = secret.metadata.name
            if name != 'karvdash-minio':
                continue
            secret_exists = True
            break

        if secret_exists and self._bucket.creation_date:
            return

        # Generate and save secret.
        secret_access_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(20))
        # kubernetes_client.update_secret(self._user.namespace,
        #                                 'karvdash-minio',
        #                                 ['AWS_ACCESS_KEY_ID=%s' % self._user.username,
        #                                  'AWS_SECRET_ACCESS_KEY=%s' % secret_access_key])
        template = Template(SECRET_S3_SECRET_TEMPLATE)
        template.NAME = 'karvdash-minio'
        template.ACCESSKEYID = self._user.username
        template.SECRETACCESSKEY = secret_access_key
        with tempfile.NamedTemporaryFile() as f:
            f.write(template.yaml.encode())
            f.seek(0)
            kubernetes_client.apply_yaml(f.name, namespace=self._user.namespace)

        # Create user, policy, and bucket in MinIO.
        if self._url.scheme in ('minio', 'minios'):
            mc_credentials = 'MC_HOST_karvdash="%s"' % '%s://%s:%s@%s:%s' % ('http' if self._url.scheme == 'minio' else 'https',
                                                                             self._url.username,
                                                                             self._url.password,
                                                                             self._url.hostname,
                                                                             self._url.port)
            mc_policy = {'Version': '2012-10-17',
                         'Statement': [{'Action': ['s3:*'],
                                        'Effect': 'Allow',
                                        'Resource': ['arn:aws:s3:::%s/*' % self.bucket_name,
                                                     'arn:aws:s3:::%s/*' % (self._bucket_prefix + '-shared')], # Add shared bucket policy here.
                                        'Sid': ''}]}
            with tempfile.NamedTemporaryFile() as f:
                f.write(json.dumps(mc_policy).encode())
                f.seek(0)
                os.system('%s mc admin policy add karvdash %s %s' % (mc_credentials, self._user.username, f.name))
            os.system('%s mc admin user add karvdash %s %s' % (mc_credentials, self._user.username, secret_access_key))
            os.system('%s mc admin policy set karvdash %s user=%s' % (mc_credentials, self._user.username, self._user.username))
        else:
            raise ValueError('Unsupported S3 domain URL')

        try:
            self._s3.create_bucket(Bucket=self.bucket_name)
        except self._s3.meta.client.exceptions.BucketAlreadyOwnedByYou:
            pass

    @property
    def name(self):
        return 'private'

    @property
    def bucket_name(self):
        return self._bucket_prefix + '-private-' + self._user.username

class SharedS3Domain(S3Domain):
    @property
    def name(self):
        return 'shared'

    @property
    def bucket_name(self):
        return self._bucket_prefix + '-shared'
