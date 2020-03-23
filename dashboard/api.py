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

from tastypie.resources import Resource
from tastypie import fields


class dict2obj(object):
    """
    Convert dictionary to object
    @source http://stackoverflow.com/a/1305561/383912
    """
    def __init__(self, d):
        self.__dict__['d'] = d

    def __getattr__(self, key):
        value = self.__dict__['d'][key]
        if type(value) == type({}):
            return dict2obj(value)

        return value

class ServiceResource(Resource):
    title = fields.CharField(attribute='title')
    content = fields.CharField(attribute='content')
    author = fields.CharField(attribute='author_name')

    class Meta:
        resource_name = 'blogs'

    def obj_get_list(self, request=None, **kwargs):
        print('***', request)
        print('***', kwargs)
        posts = []
        #your actual logic to retrieve contents from external source.

        #example
        posts.append(dict2obj(
            {
                'pk': 1,
                'title': 'Test Blog Title 1',
                'content': 'Blog Content',
                'author_name': 'User 1'
            }
        ))
        posts.append(dict2obj(
            {
                'pk': 2,
                'title': 'Test Blog Title 2',
                'content': 'Blog Content 2',
                'author_name': 'User 2'
            }
        ))

        return posts

