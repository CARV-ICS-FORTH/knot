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

from django.urls import path
from django.conf import settings
from django.contrib.auth import views as auth_views

from . import views
from . import webhooks


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('services', views.services, name='services'),
    path('service/<str:name>', views.service_info, name='service_info'),
    path('service/create/<str:name>', views.service_create, name='service_create'),
    path('service/upgrade/<str:name>', views.service_upgrade, name='service_upgrade'),
    path('templates', views.templates, name='templates'),
    path('datasets', views.datasets, name='datasets'),
    path('dataset/<str:name>', views.dataset_info, name='dataset_info'),
    path('dataset/add/<str:name>', views.dataset_add, name='dataset_add'),
    path('files', views.files, name='files'),
    path('files/upload', views.UploadView.as_view(), name='files_upload'),
    path('files/upload_complete', views.UploadCompleteView.as_view(), name='files_upload_complete'),
    path('files/<path:path>', views.files, name='files'),
    path('users', views.users, name='users'),
    path('user/edit/<str:username>', views.user_edit, name='user_edit'),
    path('user/change_password/<str:username>', views.user_change_password, name='user_change_password'),
    path('teams', views.teams, name='teams'),
    path('team/edit/<str:name>', views.team_edit, name='team_edit'),

    path('signup', views.signup, name='signup'),
    path('login', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('messages', views.messages, name='messages'),
    path('change_password', views.change_password, name='change_password'),
    path('logout', views.logout, {'next_url': settings.LOGOUT_REDIRECT_URL}, name='logout'),

    path('webhooks/pod/mutate', webhooks.pod_mutate),
    path('webhooks/pod/validate', webhooks.pod_validate),
    path('webhooks/ingress/mutate', webhooks.ingress_mutate),
    path('webhooks/ingress/validate', webhooks.ingress_validate),
]
