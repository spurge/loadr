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

from multiprocessing import Queue
from unittest import TestCase

import clustrloadr


class TestClustrloadr(TestCase):

    def test_provider(self):
        output = Queue()
        provider = clustrloadr.Provider('Localhost',
                                        output)
        provider.start(10)
        provider.run(1, 1, [{'url': 'http://thebrewery.se'}])
        provider.stop()

        lines = 0

        while True:
            try:
                data = output.get(True, 2)
            except:
                break

            if data[0] == 'data':
                self.assertRegex(data[2], '^([0-9]+,){5}[0-9]+$')
                lines += 1

        self.assertEqual(lines, 10)
