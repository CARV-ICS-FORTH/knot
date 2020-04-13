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
from .api import ServiceResource, TemplateResource


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('services', views.services, name='services'),
    path('service/create/<str:file_name>', views.service_create, name='service_create'),
    path('images', views.images, name='images'),
    path('data', views.data, name='data'),
    path('data/<path:path>', views.data, name='data'),
    path('users', views.users, name='users'),
    path('user/edit/<str:username>', views.user_edit, name='user_edit'),
    path('user/change_password/<str:username>', views.user_change_password, name='user_change_password'),

    path('signup', views.signup, name='signup'),
    path('login', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('change_password', views.change_password, name='change_password'),
    path('logout', views.logout, {'next': settings.LOGOUT_REDIRECT_URL}, name='logout'),

    path('api/services/', include(ServiceResource.urls())),
    path('api/templates/', include(TemplateResource.urls())),
]
