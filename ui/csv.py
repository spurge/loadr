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

from sys import stderr, stdout


class Csv:

    def __init__(self, input, output):
        self.input = input

    def start(self):
        while True:
            try:
                data = self.input.get(True)
            except:
                break

            if data[0] == 'data':
                stdout.write('%s\n' % data[2])

            if data[0] == 'error':
                stderr.write('%s\n' % data[2])
