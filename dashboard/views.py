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
import re

from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.contrib.auth import logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.admin.views.decorators import staff_member_required
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView

from .models import User, Message
from .forms import SignUpForm, EditUserForm, AddServiceForm, CreateServiceForm, ShowServiceForm, AddDatasetForm, CreateDatasetForm, ShowDatasetForm, AddFolderForm, AddImageFromFileForm
from .services import ServiceTemplateManager, ServiceManager
from .datasets import DatasetTemplateManager, DatasetManager
from .utils.kubernetes import KubernetesClient


@login_required
def dashboard(request):
    return redirect('services')

@login_required
def services(request):
    service_manager = ServiceManager(request.user)

    # Handle changes.
    if request.method == 'POST':
        if 'action' not in request.POST:
            Message.add(request, 'error', 'Invalid action.')
        elif request.POST['action'] == 'Add':
            form = AddServiceForm(request.POST, user=request.user)
            if form.is_valid():
                name = form.cleaned_data['name']
                return redirect('service_create', name)
            else:
                Message.add(request, 'error', 'Failed to create service. Probably invalid service name.')
        elif request.POST['action'] == 'Remove':
            name = request.POST.get('service', None)
            if name:
                try:
                    service_manager.delete(name)
                except Exception as e:
                    Message.add(request, 'error', 'Can not remove service "%s": %s' % (name, str(e)))
                else:
                    Message.add(request, 'success', 'Service "%s" removed.' % name)
        else:
            Message.add(request, 'error', 'Invalid action.')

        return redirect('services')

    # There is no hierarchy here.
    kubernetes_client = KubernetesClient()
    trail = [{'name': '<i class="fa fa-university" aria-hidden="true"></i> %s' % kubernetes_client.host}]

    # Fill in the contents.
    contents = []
    try:
        contents = service_manager.list()
    except:
        Message.add(request, 'error', 'Can not connect to Kubernetes.')

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'created'):
        request.session['services_sort_by'] = sort_by
    else:
        sort_by = request.session.get('services_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['services_order'] = order
    else:
        order = request.session.get('services_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/services.html', {'title': 'Services',
                                                       'trail': trail,
                                                       'contents': contents,
                                                       'sort_by': sort_by,
                                                       'order': order,
                                                       'add_service_form': AddServiceForm(user=request.user)})

@login_required
def service_info(request, name=''):
    next_view = request.GET.get('next', 'services')

    # Validate given name.
    template_manager = ServiceManager(request.user)
    try:
        variables = template_manager.variables(name)
    except KeyError:
        Message.add(request, 'error', 'Invalid service.')
        return redirect('services')

    form = ShowServiceForm(variables=variables)
    return render(request, 'dashboard/form.html', {'title': 'Service Values',
                                                   'form': form,
                                                   'action': None,
                                                   'next': reverse(next_view)})

@login_required
def service_create(request, name=''):
    next_view = request.GET.get('next', 'services')

    # Validate given name.
    template_manager = ServiceTemplateManager(request.user)
    try:
        chart_name, variables = template_manager.variables(name)
    except KeyError:
        Message.add(request, 'error', 'Invalid service.')
        return redirect('services')

    # Handle changes.
    if request.method == 'POST':
        form = CreateServiceForm(request.POST, variables=variables)
        if form.is_valid():
            data = request.POST.dict()

            service_manager = ServiceManager(request.user)
            try:
                service_name = service_manager.create(chart_name, variables, data)
            except Exception as e:
                Message.add(request, 'error', 'Can not create service: %s' % str(e))
            else:
                Message.add(request, 'success', 'Service "%s" created.' % service_name)

            return redirect('services')
    else:
        form = CreateServiceForm(variables=variables)

    return render(request, 'dashboard/form.html', {'title': 'Create Service',
                                                   'form': form,
                                                   'action': 'Create',
                                                   'next': reverse(next_view)})

@login_required
def templates(request):
    # There is no hierarchy here.
    template_manager = ServiceTemplateManager(request.user)
    trail = [{'name': '<i class="fa fa-university" aria-hidden="true"></i> %s' % template_manager.repo_base_url}]

    # Fill in the contents.
    contents = []
    try:
        contents = template_manager.list()
    except:
        Message.add(request, 'error', 'Can not list templates.')

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'description', 'singleton', 'private'):
        request.session['templates_sort_by'] = sort_by
    else:
        sort_by = request.session.get('templates_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['templates_order'] = order
    else:
        order = request.session.get('templates_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/templates.html', {'title': 'Templates',
                                                        'trail': trail,
                                                        'contents': contents,
                                                        'sort_by': sort_by,
                                                        'order': order})

@login_required
def datasets(request):
    if not settings.DATASETS_AVAILABLE:
        return redirect('dashboard')

    dataset_manager = DatasetManager(request.user)

    # Handle changes.
    if request.method == 'POST':
        if 'action' not in request.POST:
            Message.add(request, 'error', 'Invalid action.')
        elif request.POST['action'] == 'Add':
            form = AddDatasetForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data['name']
                return redirect('dataset_add', name)
            else:
                Message.add(request, 'error', 'Failed to add dataset. Probably invalid dataset name.')
        elif request.POST['action'] == 'Delete':
            name = request.POST.get('name', None)
            if name:
                try:
                    dataset_manager.delete(name)
                except Exception as e:
                    Message.add(request, 'error', 'Can not delete dataset "%s": %s' % (name, str(e)))
                else:
                    Message.add(request, 'success', 'Dataset "%s" deleted.' % name)
        else:
            Message.add(request, 'error', 'Invalid action.')

        return redirect('datasets')

    # There is no hierarchy here.
    kubernetes_client = KubernetesClient()
    trail = [{'name': '<i class="fa fa-university" aria-hidden="true"></i> %s' % kubernetes_client.host}]

    # Fill in the contents.
    contents = []
    try:
        for dataset in dataset_manager.list():
            try:
                dataset_type = dataset['type']
                if dataset_type == 'COS':
                    dataset_type = 'S3'
                    endpoint = '%s/%s' % (dataset['endpoint'], dataset['bucket'])
                elif dataset_type == 'H3':
                    endpoint = '%s/%s' % (dataset['storageUri'], dataset['bucket'])
                elif dataset_type == 'ARCHIVE':
                    endpoint = dataset['url']
                contents.append({'name': dataset['name'],
                                 'type': dataset_type,
                                 'endpoint': endpoint})
            except:
                pass
    except:
        Message.add(request, 'error', 'Can not connect to Kubernetes.')

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'type', 'endpoint'):
        request.session['datasets_sort_by'] = sort_by
    else:
        sort_by = request.session.get('datasets_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['datasets_order'] = order
    else:
        order = request.session.get('datasets_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/datasets.html', {'title': 'Datasets',
                                                       'trail': trail,
                                                       'contents': contents,
                                                       'sort_by': sort_by,
                                                       'order': order,
                                                       'add_dataset_form': AddDatasetForm()})

@login_required
def dataset_info(request, name=''):
    next_view = request.GET.get('next', 'datasets')

    # Validate given name.
    dataset_manager = DatasetManager(request.user)
    try:
        variables = dataset_manager.variables(name)
    except KeyError:
        Message.add(request, 'error', 'Invalid dataset.')
        return redirect('datasets')

    form = ShowDatasetForm(variables=variables)
    return render(request, 'dashboard/form.html', {'title': 'Dataset Values',
                                                   'form': form,
                                                   'action': None,
                                                   'next': reverse(next_view)})

@login_required
def dataset_add(request, name=''):
    next_view = request.GET.get('next', 'datasets')

    # Validate given name.
    dataset_manager = DatasetTemplateManager(request.user)
    try:
        chart_name, variables = dataset_manager.variables(name)
    except KeyError:
        Message.add(request, 'error', 'Invalid dataset.')
        return redirect('datasets')

    # Handle changes.
    if request.method == 'POST':
        form = CreateDatasetForm(request.POST, variables=variables)
        if form.is_valid():
            data = request.POST.dict()

            dataset_manager = DatasetManager(request.user)
            try:
                dataset_name = dataset_manager.create(chart_name, variables, data, set_local_data=False)
            except Exception as e:
                Message.add(request, 'error', 'Can not create dataset: %s' % str(e))
            else:
                Message.add(request, 'success', 'Dataset "%s" created.' % dataset_name)

            return redirect('datasets')
    else:
        form = CreateDatasetForm(variables=variables)

    return render(request, 'dashboard/form.html', {'title': 'Add Dataset',
                                                   'form': form,
                                                   'action': 'Add',
                                                   'next': reverse(next_view)})

@login_required
def files(request, path='/'):
    # Get user file domains.
    file_domains = request.user.file_domains if not getattr(request.user, 'is_impersonate', False) else User.objects.get(pk=request.user.pk).file_domains

    # Normalize given path and split.
    path = os.path.normpath(path)
    path = path.lstrip('/')
    if path == '':
        path = request.session.get('files_path', list(file_domains.keys())[0]) # First is the default.
    path_components = [p for p in path.split('/') if p]

    # Figure out the real path we are working on.
    if path_components[0] not in file_domains.keys():
        Message.add(request, 'error', 'Invalid path.')
        request.session.pop('files_path', None)
        return redirect('files')

    request.session['files_path'] = path # Save current path.
    domain = path_components[0]
    path_worker = file_domains[domain].path_worker(path_components[1:])

    # Handle changes.
    if request.method == 'POST':
        if 'action' not in request.POST:
            Message.add(request, 'error', 'Invalid action.')
        elif request.POST['action'] == 'Create':
            form = AddFolderForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data['name']
                if path_worker.exists(name):
                    Message.add(request, 'error', 'Can not add "%s". An item with the same name already exists.' % name)
                else:
                    path_worker.mkdir(name)
                    Message.add(request, 'success', 'Folder "%s" created.' % name)
            else:
                # XXX Show form errors in messages.
                pass
        elif request.POST['action'] == 'Download':
            name = request.POST['name']
            if not path_worker.isdir(name):
                Message.add(request, 'error', 'Can not download "%s".' % name)
            else:
                response = HttpResponse(content_type='application/zip')
                path_worker.download(name, response)
                response['Content-Disposition'] = 'attachment; filename="%s.zip"' % re.sub(r'[^A-Za-z0-9 \-_]+', '', name)
                return response
        elif request.POST['action'] == 'Delete':
            name = request.POST.get('filename', None)
            if name:
                if not path_worker.exists(name):
                    Message.add(request, 'error', 'Item "%s" not found in folder.' % name)
                else:
                    try:
                        if path_worker.isfile(name):
                            path_worker.remove(name)
                        else:
                            path_worker.rmdir(name)
                    except Exception as e: # noqa: F841
                        # Message.add(request, 'error', 'Failed to delete "%s": %s.' % (name, str(e)))
                        Message.add(request, 'error', 'Failed to delete "%s". Probably not permitted or directory not empty.' % name)
                    else:
                        Message.add(request, 'success', 'Item "%s" deleted.' % name)
        else:
            Message.add(request, 'error', 'Invalid action.')

        return redirect('files', path)

    # Respond appropriately if the path is not a directory.
    if path_worker.isfile():
        request.session['files_path'] = os.path.dirname(path) # Save path to folder.
        parent_path_worker = file_domains[path_components[0]].path_worker(path_components[1:-1])
        name = path_components[-1]
        return FileResponse(parent_path_worker.open(name, 'rb'), as_attachment=True, filename=name)
    if not path_worker.isdir():
        request.session.pop('files_path', None)
        # Message.add(request, 'error', 'Invalid path.')
        return redirect('files')

    # This is a directory. Leave a trail of breadcrumbs.
    trail = []
    trail.append({'name': '<i class="fa fa-hdd-o" aria-hidden="true"></i>',
                  'url': reverse('files', args=[domain]) if len(path_components) != 1 else None})
    for i, path_component in enumerate(path_components[1:]):
        trail.append({'name': path_component,
                      'url': reverse('files', args=[os.path.join(*path_components[:i + 2])]) if i != (len(path_components) - 2) else None})

    # Fill in the contents.
    contents = path_worker.listdir()
    for content in contents:
        content.update({'url': reverse('files', args=[os.path.join(path, content['name'])])})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'modified', 'size'):
        request.session['files_sort_by'] = sort_by
    else:
        sort_by = request.session.get('files_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['files_order'] = order
    else:
        order = request.session.get('files_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/files.html', {'title': 'Files',
                                                    'domain': domain,
                                                    'path': os.path.join(*path_components[1:]) if path_components[1:] else '',
                                                    'trail': trail,
                                                    'contents': contents,
                                                    'sort_by': sort_by,
                                                    'order': order,
                                                    'add_folder_form': AddFolderForm(),
                                                    'add_image_from_file_form': AddImageFromFileForm()})

class UploadView(ChunkedUploadView):
    pass

class UploadCompleteView(ChunkedUploadCompleteView):
    do_md5_check = False

    def on_completion(self, uploaded_file, request):
        '''
        Placeholder method to define what to do when upload is complete.
        '''

        # Get user file domains.
        file_domains = request.user.file_domains if not getattr(request.user, 'is_impersonate', False) else User.objects.get(pk=request.user.pk).file_domains

        path_worker = file_domains[request.POST['domain']].path_worker(request.POST['path'].split('/'))
        if path_worker.exists(uploaded_file.name):
            Message.add(request, 'error', 'Can not add "%s". An item with the same name already exists.' % uploaded_file.name)
            return
        filename = os.path.join(settings.MEDIA_ROOT, uploaded_file.file.name)
        path_worker.upload(filename, uploaded_file.name)

    def get_response_data(self, chunked_upload, request):
        '''
        Data for the response. Should return a dictionary-like object.
        Called *only* if POST is successful.
        '''
        filename = os.path.join(settings.MEDIA_ROOT, chunked_upload.file.name)
        chunked_upload.delete(delete_file=os.path.exists(filename))
        return {}

@staff_member_required
def users(request):
    # Handle changes.
    if request.method == 'POST':
        if 'action' not in request.POST:
            Message.add(request, 'error', 'Invalid action.')
        elif request.POST['action'] in ('Activate', 'Deactivate', 'Promote', 'Demote'):
            action = request.POST['action']
            username = request.POST.get('username', None)
            if username and username != request.user.username:
                try:
                    user = User.objects.get(username=username)
                    if action == 'Activate':
                        user.is_active = True
                        user.create_namespace(request)
                        user.update_kubernetes_credentials()
                    elif action == 'Deactivate':
                        user.is_active = False
                        user.delete_kubernetes_credentials()
                    elif action in ('Promote', 'Demote'):
                        user.is_staff = True if action == 'Promote' else False
                    user.save()
                    User.export_to_htpasswd(settings.HTPASSWD_EXPORT_DIR)
                    Message.add(request, 'success', 'User "%s" %s.' % (username, action.lower() + 'd'))
                except User.DoesNotExist:
                    pass
            else:
                Message.add(request, 'error', 'Invalid username')
        elif request.POST['action'] == 'Delete':
            username = request.POST.get('username', None)
            if username and username != request.user.username:
                try:
                    user = User.objects.get(username=username)
                    try:
                        user.delete_namespace()
                    except Exception as e:
                        Message.add(request, 'error', 'Failed to delete user "%s": %s.' % (username, str(e)))
                    else:
                        user.delete()
                        User.export_to_htpasswd(settings.HTPASSWD_EXPORT_DIR)
                        Message.add(request, 'success', 'User "%s" deleted.' % username)
                except User.DoesNotExist:
                    pass
            else:
                Message.add(request, 'error', 'Invalid username')
        else:
            Message.add(request, 'error', 'Invalid action.')

        return redirect('users')

    # Fill in the contents.
    contents = []
    for user in User.objects.all():
        contents.append({'id': user.id,
                         'username': user.username,
                         'email': user.email,
                         'active': 1 if user.is_active else 0,
                         'admin': 1 if user.is_staff else 0,
                         'actions': True if user.username != request.user.username else False})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('username', 'email', 'active', 'admin'):
        request.session['users_sort_by'] = sort_by
    else:
        sort_by = request.session.get('users_sort_by', 'username')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['users_order'] = order
    else:
        order = request.session.get('users_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/users.html', {'title': 'Users',
                                                    'contents': contents,
                                                    'sort_by': sort_by,
                                                    'order': order})

@staff_member_required
def user_edit(request, username):
    # Validate given username.
    if username == request.user.username:
        Message.add(request, 'error', 'Invalid username.')
        return redirect('users')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        Message.add(request, 'error', 'Invalid username.')
        return redirect('users')

    if request.method == 'POST':
        form = EditUserForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user.email = email
            user.save()
            Message.add(request, 'success', 'User "%s" edited.' % username)
            return redirect('users')
    else:
        form = EditUserForm()
        form.fields['email'].initial = user.email

    return render(request, 'dashboard/form.html', {'title': 'Edit User',
                                                   'form': form,
                                                   'action': 'Edit',
                                                   'next': reverse('users')})

@staff_member_required
def user_change_password(request, username):
    # Validate given username.
    if username == request.user.username:
        Message.add(request, 'error', 'Invalid username.')
        return redirect('users')
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        Message.add(request, 'error', 'Invalid username.')
        return redirect('users')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.update_kubernetes_credentials()
            User.export_to_htpasswd(settings.HTPASSWD_EXPORT_DIR)
            Message.add(request, 'success', 'Password changed for user "%s".' % username)
            return redirect('users')
    else:
        form = SetPasswordForm(user)

    return render(request, 'dashboard/form.html', {'title': 'Change User Password',
                                                   'form': form,
                                                   'action': 'Change',
                                                   'next': reverse('users')})

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
def messages(request):
    # Fill in the contents.
    contents = []
    for message in request.user.messages.filter():
        contents.append({'label': message.label,
                         'level': message.level,
                         'message': message.message,
                         'created': message.created})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('created'):
        request.session['messages_sort_by'] = sort_by
    else:
        sort_by = request.session.get('messages_sort_by', 'created')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['messages_order'] = order
    else:
        order = request.session.get('messages_order', 'desc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/messages.html', {'title': 'Messages',
                                                       'contents': contents,
                                                       'sort_by': sort_by,
                                                       'order': order})

@login_required
def change_password(request):
    next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            user.update_kubernetes_credentials()
            User.export_to_htpasswd(settings.HTPASSWD_EXPORT_DIR)
            Message.add(request, 'success', 'Password successfully changed.')
            return redirect(next_url)
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'dashboard/form.html', {'title': 'Change Password',
                                                   'form': form,
                                                   'action': 'Change',
                                                   'next': next_url})

@login_required
def logout(request, next_url):
    auth_logout(request)
    return redirect(next_url)
