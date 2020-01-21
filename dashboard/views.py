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

from django.shortcuts import render, redirect, reverse
from django.http import FileResponse
from django.conf import settings
from django.contrib.auth import login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime

from .forms import SignUpForm, ChangePasswordForm


@login_required
def dashboard(request):
    return render(request, 'dashboard/dashboard.html', {'title': 'Dashboard'})

@login_required
def code(request):
    return render(request, 'dashboard/code.html', {'title': 'Code'})

@login_required
def data(request, path='/'):
    # Normalize given path and split.
    path = os.path.normpath(path)
    path = path.lstrip('/')
    if path == '':
        path = 'local'
    path_components = [p for p in path.split('/') if p]

    # Figure out the real path we are working on.
    for domain, folder in settings.DATA_DOMAINS.items():
        if path_components[0] == domain:
            real_path = os.path.join(folder, '/'.join(path_components[1:]))
            break
    else:
        messages.error(request, 'Unknown path.')
        return redirect('data')

    # Respond appropriately if the path is not a directory.
    if os.path.isfile(real_path):
        return FileResponse(open(real_path, 'rb'), as_attachment=True, filename=os.path.basename(real_path))
    if not os.path.isdir(real_path):
        messages.error(request, 'Invalid path.')
        return redirect('data')

    # This is a directory. Leave a trail of breadcrumbs.
    trail = []
    trail.append({'name': '<i class="fa fa-hdd-o" aria-hidden="true"></i>',
                  'url': reverse('data', args=[domain]) if len(path_components) != 1 else None})
    for i, path_component in enumerate(path_components[1:]):
        trail.append({'name': path_component,
                      'url': reverse('data', args=[os.path.join(*path_components[:i + 2])]) if i != (len(path_components) - 2) else None})

    # Fill in the contents.
    contents = []
    for file_name in os.listdir(real_path):
        file_path = os.path.join(real_path, file_name)
        if os.path.isdir(file_path):
            file_type = 'dir'
        elif os.path.isfile(file_path):
            file_type = 'file'
        else:
            continue
        mtime = os.path.getmtime(file_path)
        contents.append({'name': file_name,
                         'timestamp': mtime,
                         'modified': datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M'),
                         'type': file_type,
                         'size': os.path.getsize(file_path),
                         'url': reverse('data', args=[os.path.join(path, file_name)])})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'modified', 'size'):
        request.session['data_sort_by'] = sort_by
    else:
        sort_by = request.session.get('data_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['data_order'] = order
    else:
        order = request.session.get('data_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by if sort_by != 'modified' else 'timestamp'],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/data.html', {'title': 'Data',
                                                   'domain': domain,
                                                   'trail': trail,
                                                   'contents': contents,
                                                   'sort_by': sort_by,
                                                   'order': order})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            message = 'Your account has been created, but in order to login an administrator will have to activate it.'
            return render(request, 'dashboard/signup.html', {'message': message,
                                                                'next': settings.LOGIN_REDIRECT_URL})
    else:
        form = SignUpForm()
    return render(request, 'dashboard/signup.html', {'form': form,
                                                     'next': settings.LOGIN_REDIRECT_URL})

@login_required
def change_password(request):
    next = request.GET.get('next', settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password successfully changed.')
            return redirect(next)
    else:
        form = ChangePasswordForm(request.user)
    return render(request, 'dashboard/change_password.html', {'form': form,
                                                              'next': next})

@login_required
def logout(request, next):
    auth_logout(request)
    return redirect(next)
