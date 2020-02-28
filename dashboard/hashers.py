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

from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import get_random_string, constant_time_compare
from passlib.hash import apr_md5_crypt


class APR1PasswordHasher(BasePasswordHasher):
    '''
    Password hashing using the Apache-defined APR1 hashing format
    '''

    algorithm = "apr1"

    def salt(self):
        return get_random_string(8)

    def encode(self, password, salt):
        assert password is not None
        assert salt and '$' not in salt
        return apr_md5_crypt.hash(password, salt=salt)[1:]

    def verify(self, password, encoded):
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return constant_time_compare(encoded, self.encode(password, salt))

    def safe_summary(self, encoded):
        algorithm, salt, data = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return OrderedDict([
            (_('algorithm'), algorithm),
            (_('salt'), salt),
            (_('hash'), mask_hash(data, show=3)),
        ])

    def harden_runtime(self, password, encoded):
        pass
