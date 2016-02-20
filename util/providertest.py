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

import unittest


class ProviderTest(unittest.TestCase):

    def tearDown(self):
        self.provider.shutdown()

    def test_create_instance(self):
        self.provider.create_instances(1)

        self.provider.run_worker([{'method': 'get',
                                   'url': 'https://google.com?q=loadr'}])

        self.provider.remove_instances()
