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
import sys

from io import StringIO


class ProviderTest(unittest.TestCase):

    def tearDown(self):
        self.provider.remove_instances()
        self.provider.shutdown()

    def test_create_instances(self):
        self.assertIsNotNone(self.provider)

        self.provider.create_instances(1)
        self.assertEqual(len(self.provider.instances), 1)

        output = StringIO()
        self.provider.run_worker([{'method': 'get',
                                   'url': 'https://google.com?q=loadr'}],
                                 output)

        self.assertGreater(len(output.getvalue()), 0)
        output.close()

        self.provider.remove_instances()
        self.assertIsNone(self.provider.instances)
