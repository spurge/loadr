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

from multiprocessing import get_context
from unittest import TestCase

from ui import get_ui

class TestCsv(TestCase):

    def test_csv(self):
        mp = get_context('fork')
        queue = mp.Queue()
        input, output = mp.Pipe()
        csv = get_ui('Csv', input=queue, output=input)
        ui_process = mp.Process(target=csv.start)
        ui_process.start()

        command_run = output.recv()
        self.assertEqual(command_run, ('command', 'run'))

        command_quit = output.recv()
        self.assertEqual(command_quit, ('command', 'quit'))

        ui_process.terminate()
