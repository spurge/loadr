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

import sys

from multiprocessing import Queue
from unittest import TestCase

import clustrloadr


class TestClustrloadr(TestCase):

    def test_session(self):
        output = Queue()
        session = clustrloadr.Session(output)

        session.providers({'provider-1': {'type': 'Localhost'},
                           'provider-2': {'type': 'Localhost'}})
        session.requests([{'url': 'http://thebrewery.se'}])

        session.start([{'provider': 'provider-1',
                        'instances': 2,
                        'concurrency': 1,
                        'repeat': 2},
                       {'provider': 'provider-2',
                        'instances': 3,
                        'concurrency': 2,
                        'repeat': 1}])
        session.run()
        session.run()
        session.stop()

        lines = 0

        while True:
            try:
                data = output.get(True, 2)
            except:
                break

            if data[0] == 'data':
                self.assertRegex(data[2], '^([0-9]+,){5}[0-9]+$')
                lines += 1

        self.assertEqual(lines, 20)
