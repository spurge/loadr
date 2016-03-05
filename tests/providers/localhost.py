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
from multiprocessing import Process, Queue

from providers import Localhost


class TestLocalhost(unittest.TestCase):

    def setUp(self):
        self.output = Queue()
        sels.provider = Localhost(output=self.output)

    def tearDown(self):
        self.provider.remove_instances()
        self.provider.shutdown()

    def test_create_instances(self):
        self.assertIsNotNone(self.provider)

        self.provider.create_instances(1)
        self.assertEqual(len(self.provider.instances), 1)

        self.provider.run_multiple_workers(concurrency=1,
                                           repeat=1,
                                           requests=[{'method': 'get',
                                                      'url': 'https://google.com?q=loadr'}])

        stdout = ''
        stderr = ''

        while True:
            data = self.output.get(True, 120)

            if data[0] == 'data':
                sys.stdout.write(data[2])
                stdout += data[2]

            if data[0] == 'error':
                sys.stderr.write(data[2])
                stderr += data[2]

            if data[0] == 'status' and data[2] == 'ended':
                break

        self.assertGreater(len(stdout), 0)
        self.assertGreater(1, len(stderr))

        self.provider.remove_instances()
        self.assertGreater(1, len(self.provider.instances))
