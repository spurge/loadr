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
from time import time

from clustrloadr import Session
from providers.localhost import Localhost


class TestLocalhost(unittest.TestCase):

    def setUp(self):
        self.output = Queue()
        self.provider = Localhost(output=self.output)
        self.session = Session(self.output)
        self.session.providers({'provider-1': {'type': 'Localhost'},
                                'provider-2': {'type': 'Localhost'}})

    def tearDown(self):
        self.provider.remove_instances()
        self.provider.shutdown()
        self.session.stop()

    def test_create_instances(self):
        self.assertIsNotNone(self.provider)

        self.provider.create_instances(1)
        self.provider.wait_for_running_instances()
        self.assertEqual(len(self.provider.instances), 1)

        starttime = time() + 10

        self.provider.run_multiple_workers(concurrency=2,
                                           repeat=3,
                                           requests=[{'method': 'get',
                                                      'url': 'https://google.com?q=loadr'}],
                                           starttime=starttime)

        stdout = []
        stderr = ''

        while True:
            try:
                data = self.output.get(True, 2)
            except:
                break

            if data[0] == 'data':
                stdout.append(data)

            if data[0] == 'error':
                sys.stderr.write(data[2])
                stderr += data[2]

            if data[0] == 'status' and data[2] == 'ended':
                break

        self.assertEqual(len(stdout), 6)
        self.assertEqual(len(stderr), 0)

        self.provider.remove_instances()
        self.provider.wait_for_removed_instances()
        self.assertEqual(len(self.provider.instances), 0)

    def test_session(self):
        self.session.requests([{'url': 'http://thebrewery.se'}])
        self.session.start([{'provider': 'provider-1',
                             'instances': 2,
                             'concurrency': 1,
                             'repeat': 2},
                            {'provider': 'provider-2',
                             'instances': 3,
                             'concurrency': 2,
                             'repeat': 1}])
        self.session.run()
        self.session.run()
        self.session.stop()

        lines = 0

        while True:
            try:
                data = self.output.get(True, 2)
            except:
                break

            if data[0] == 'data':
                self.assertRegex(data[2], '^([0-9]+,){5}[0-9]+$')
                lines += 1

        self.assertEqual(lines, 20)
