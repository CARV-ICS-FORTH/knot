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

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from .models import User
from .services import ServiceTemplateManager
from .datasets import DatasetTemplateManager


validate_image_name = RegexValidator(r'^[0-9a-z\-\.]*$', 'Only alphanumeric characters, dash, and period are allowed.')
validate_image_tag = RegexValidator(r'^[0-9a-zA-Z_\-\.]*$', 'Only alphanumeric characters, dash, underscore, and period are allowed.')

validate_username = RegexValidator(r'^[a-z0-9]+$', 'Only lowercase alphanumeric characters are allowed.')

validate_kubernetes_label = RegexValidator(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', 'Only lowercase alphanumeric characters and dash are allowed.')

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Please use a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].validators.append(validate_username)
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters and digits only.'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'password1',
            'password2',
            'email',
            Submit('submit', 'Submit', css_class='btn-success btn-lg btn-block')
        )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with that email already exists.')
        return email

class AddServiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        template_manager = ServiceTemplateManager(self.user)
        try:
            templates = sorted(template_manager.list(),
                               key=lambda x: x['name'],
                               reverse=False)
        except:
            templates = []
        self.fields['name'] = forms.ChoiceField(label='Service to create',
                                                choices=[(t['name'], '%s: %s' % (t['name'], t['description'])) for t in templates])

class CreateServiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        variables = kwargs.pop('variables')
        super().__init__(*args, **kwargs)
        for variable in variables:
            label = variable['label']
            if label.startswith('data.karvdash.'):
                continue
            kwargs = {'validators': [validate_kubernetes_label], 'required': True} if label == 'name' else {'required': False}
            if label.startswith('data.'):
                label = label[5:]
            self.fields[variable['label']] = forms.CharField(label=label.replace('.', ' ').capitalize(),
                                                             initial=variable.get('default'),
                                                             help_text=variable.get('help'),
                                                             **kwargs)

class ShowServiceForm(CreateServiceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.disabled = True

class AddDatasetForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        template_manager = DatasetTemplateManager(None)
        try:
            templates = sorted(template_manager.list(),
                               key=lambda x: x['name'],
                               reverse=False)
        except:
            templates = []
        self.fields['name'] = forms.ChoiceField(label='Dataset to add',
                                                choices=[(t['name'], '%s: %s' % (t['name'], t['description'])) for t in templates])

class CreateDatasetForm(CreateServiceForm):
    pass

class ShowDatasetForm(ShowServiceForm):
    pass

class AddFolderForm(forms.Form):
    name = forms.CharField(label='Name for the new folder', min_length=1, max_length=255, initial='New Folder')

class AddImageFromFileForm(forms.Form):
    name = forms.CharField(label='Image name', min_length=1, max_length=128, validators=[validate_image_name])
    tag = forms.CharField(label='Tag', min_length=1, max_length=128, validators=[validate_image_tag])

class EditUserForm(forms.Form):
    email = forms.EmailField(label='Email')
