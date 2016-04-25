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

import random

from multiprocessing import get_context
from unittest import TestCase

from ui import get_ui

class TestText(TestCase):

    def test_text(self):
        mp = get_context('fork')
        queue = mp.Queue()
        input, output = mp.Pipe()
        text = get_ui('Text', input=queue, output=input)
        ui_process = mp.Process(target=text.start)
        ui_process.start()

        command_run = output.recv()
        self.assertEqual(command_run, ('command', 'run'))

        for i in range(0, random.randint(10, 100)):
            queue.put(('data', '', ','.join(['0',
                                             '0',
                                             '0',
                                             '200',
                                             str(i * random.randint(1, 10)),
                                             str(i * random.randint(1, 10))])))

        command_quit = output.recv()
        self.assertEqual(command_quit, ('command', 'quit'))

        ui_process.terminate()
