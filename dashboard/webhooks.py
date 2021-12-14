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

import json
import jsonpatch
import copy
import base64

from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import User
from .utils.inject import inject_volumes, validate_hostpath_volumes


@require_POST
@csrf_exempt
def mutate(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        assert(data['kind'] == 'AdmissionReview')
        assert(data['request']['operation'] == 'CREATE')
        uid = data['request']['uid']
        namespace = data['request']['namespace']
        assert(namespace.startswith('karvdash-'))
        user = User.objects.get(username=namespace[len('karvdash-'):])
        service = copy.deepcopy(data['request']['object'])
    except:
        return HttpResponseBadRequest()

    inject_volumes([service], user.file_domains, add_api_settings=True)
    inject_volumes([service], user.dataset_volumes, is_datasets=True)
    patch = jsonpatch.JsonPatch.from_diff(data['request']['object'], service)
    encoded_patch = base64.b64encode(patch.to_string().encode('utf-8')).decode('utf-8')

    response = JsonResponse({'apiVersion': 'admission.k8s.io/v1',
                             'kind': 'AdmissionReview',
                             'response': {'uid': uid,
                                          'allowed': True,
                                          'status': {'message': 'Adding Karvdash volumes and API settings'},
                                          'patchType': 'JSONPatch',
                                          'patch': encoded_patch}})
    response['X-Log-User'] = user.username
    return response

@require_POST
@csrf_exempt
def validate(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        assert(data['kind'] == 'AdmissionReview')
        assert(data['request']['operation'] == 'CREATE')
        uid = data['request']['uid']
        namespace = data['request']['namespace']
        assert(namespace.startswith('karvdash-'))
        user = User.objects.get(username=namespace[len('karvdash-'):])
        service = copy.deepcopy(data['request']['object'])
    except:
        return HttpResponseBadRequest()

    response = JsonResponse({'apiVersion': 'admission.k8s.io/v1',
                             'kind': 'AdmissionReview',
                             'response': {'uid': uid,
                                          'allowed': validate_hostpath_volumes([service], user.file_domains, other_allowed_paths=settings.ALLOWED_HOSTPATH_DIRS),
                                          'status': {'message': 'Checking for unauthorized volumes'}}})
    response['X-Log-User'] = user.username
    return response
