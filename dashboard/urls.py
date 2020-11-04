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

from django.urls import path, include
from django.conf import settings
from django.contrib.auth import views as auth_views

from . import views
from . import webhooks
from .api import ServiceResource, TemplateResource


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('services', views.services, name='services'),
    path('service/create/<str:identifier>', views.service_create, name='service_create'),
    path('templates', views.templates, name='templates'),
    path('template/<str:identifier>', views.template_download, name='template_download'),
    path('images', views.images, name='images'),
    path('image/<path:name>', views.image_info, name='image_info'),
    path('datasets', views.datasets, name='datasets'),
    path('dataset/add/<str:identifier>', views.dataset_add, name='dataset_add'),
    path('dataset/<str:name>', views.dataset_download, name='dataset_download'),
    path('files', views.files, name='files'),
    path('files/<path:path>', views.files, name='files'),
    path('users', views.users, name='users'),
    path('user/edit/<str:username>', views.user_edit, name='user_edit'),
    path('user/change_password/<str:username>', views.user_change_password, name='user_change_password'),

    path('signup', views.signup, name='signup'),
    path('login', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('change_password', views.change_password, name='change_password'),
    path('logout', views.logout, {'next_url': settings.LOGOUT_REDIRECT_URL}, name='logout'),

    path('webhooks/mutate', webhooks.mutate),
    path('webhooks/validate', webhooks.validate),

    path('api/services/', include(ServiceResource.urls())),
    path('api/templates/', include(TemplateResource.urls())),
]
