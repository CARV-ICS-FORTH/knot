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
from urllib.parse import urlparse

from .models import User
from .utils.inject import inject_volumes, inject_variables, validate_hostpath_volumes, inject_ingress_auth, validate_ingress_host


def validate_admission_review(request, allowed_operations):
    data = json.loads(request.body.decode('utf-8'))
    assert(data['kind'] == 'AdmissionReview')
    assert(data['request']['operation'] in allowed_operations)
    request_uid = data['request']['uid']
    namespace = data['request']['namespace']
    assert(namespace.startswith('knot-'))
    user = User.objects.get(username=namespace[len('knot-'):])
    request_service = data['request']['object']

    return request_uid, request_service, user

@require_POST
@csrf_exempt
def pod_mutate(request):
    try:
        request_uid, request_service, user = validate_admission_review(request, ['CREATE'])
        service = copy.deepcopy(request_service)
    except:
        return HttpResponseBadRequest()

    inject_volumes([service], user.file_domains)
    inject_variables([service], user)
    patch = jsonpatch.JsonPatch.from_diff(request_service, service)
    encoded_patch = base64.b64encode(patch.to_string().encode('utf-8')).decode('utf-8')

    response = JsonResponse({'apiVersion': 'admission.k8s.io/v1',
                             'kind': 'AdmissionReview',
                             'response': {'uid': request_uid,
                                          'allowed': True,
                                          'status': {'message': 'Adding Knot volumes'},
                                          'patchType': 'JSONPatch',
                                          'patch': encoded_patch}})
    response['X-Log-User'] = user.username
    return response

@require_POST
@csrf_exempt
def pod_validate(request):
    try:
        request_uid, request_service, user = validate_admission_review(request, ['CREATE'])
    except:
        return HttpResponseBadRequest()

    response = JsonResponse({'apiVersion': 'admission.k8s.io/v1',
                             'kind': 'AdmissionReview',
                             'response': {'uid': request_uid,
                                          'allowed': validate_hostpath_volumes([request_service], user.file_domains, other_allowed_paths=settings.ALLOWED_HOSTPATH_DIRS),
                                          'status': {'message': 'Unauthorized volumes check'}}})
    response['X-Log-User'] = user.username
    return response

@require_POST
@csrf_exempt
def ingress_mutate(request):
    try:
        request_uid, request_service, user = validate_admission_review(request, ['CREATE'])
        service = copy.deepcopy(request_service)
    except:
        return HttpResponseBadRequest()

    ingress_url = urlparse(settings.INGRESS_URL)
    if settings.VOUCH_URL:
        auth_config = {'vouch_url': settings.VOUCH_URL,
                       'username': user.username}
    else:
        auth_config = {'secret': 'knot-auth',
                       'realm': 'Authentication Required - %s' % settings.DASHBOARD_TITLE}
    inject_ingress_auth([service], auth_config, redirect_ssl=(ingress_url.scheme == 'https'))
    patch = jsonpatch.JsonPatch.from_diff(request_service, service)
    encoded_patch = base64.b64encode(patch.to_string().encode('utf-8')).decode('utf-8')

    response = JsonResponse({'apiVersion': 'admission.k8s.io/v1',
                             'kind': 'AdmissionReview',
                             'response': {'uid': request_uid,
                                          'allowed': True,
                                          'status': {'message': 'Adding Knot authentication'},
                                          'patchType': 'JSONPatch',
                                          'patch': encoded_patch}})
    response['X-Log-User'] = user.username
    return response

@require_POST
@csrf_exempt
def ingress_validate(request):
    try:
        request_uid, request_service, user = validate_admission_review(request, ['CREATE'])
    except:
        return HttpResponseBadRequest()

    ingress_url = urlparse(settings.INGRESS_URL)
    ingress_host = '%s:%s' % (ingress_url.hostname, ingress_url.port) if ingress_url.port else ingress_url.hostname

    response = JsonResponse({'apiVersion': 'admission.k8s.io/v1',
                             'kind': 'AdmissionReview',
                             'response': {'uid': request_uid,
                                          'allowed': validate_ingress_host([request_service], user.username, ingress_host),
                                          'status': {'message': 'Valid hostname check'}}})
    response['X-Log-User'] = user.username
    return response
