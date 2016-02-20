"""
Copyright (c) 2016 Olof Montin <olof@thebrewery.se>

This file is part of loadr.

loadr is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

loadr is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with loadr.  If not, see <http://www.gnu.org/licenses/>.
"""

from providers.awsec2 import Awsec2
from util.providertest import ProviderTest


class TestAwsec2(ProviderTest):

    def setUp(self):
        self.provider = Awsec2({'profile': 'loadr',
                                'type':    't2.micro',
                                'image':   'ami-d22932be',
                                'region':  'eu-central-1'})
