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

from functools import partial
from io import StringIO
from multiprocessing import Queue
from requests import Response, Session
from unittest import TestCase

import wrkloadr


class HistoryMockup():

    def __init__(self, headers, body):
        self.headers = headers
        self.body = body

    def json(self):
        return self.body


class TestWrkloadr(TestCase):

    def test_parseconfig(self):
        history = {'0': HistoryMockup({'Content-Type': 'application/json'},
                     {'some-content': {'subcontent': 'ok'}}),
                   '1': HistoryMockup({'Some-custom-header': 'data'},
                     {'super-content': '123'})}

        data = {'headers': {
                'custom-header': '{{from(0).json.some-content.subcontent}} value and {{from(1).headers.Some-custom-header}}'},
               'body': {
                   'from-header-0': {
                       'header': '{{from(0).headers.Content-Type}}/stuff'},
                    'from-body-1': 'body: {{from(1).json.super-content}}'}}

        parsed = wrkloadr.parseconfig(data, history)

        self.assertEqual(parsed['headers']['custom-header'],
                         'ok value and data')
        self.assertEqual(parsed['body']['from-header-0'],
                         {'header': 'application/json/stuff'})
        self.assertEqual(parsed['body']['from-body-1'],
                         'body: 123')

    def test_send(self):
        sess = Session()
        res = wrkloadr.send({'method': 'GET',
                             'url': 'http://thebrewery.se/',
                             'headers': None,
                             'body': None},
                            sess,
                            [])
        sess.close()
        self.assertIsInstance(res, Response)

    def test_singlerepeater(self):
        lines = StringIO()

        def writer(lines, *args):
            lines.write('.')
            self.assertEqual(len(args), 6)

            for val in args:
                self.assertIsInstance(val, int)

        wrkloadr.singlerepeater(2,
                                partial(writer, lines),
                                [{'method': 'GET',
                                  'url': 'http://thebrewery.se/',
                                  'headers': None,
                                  'body': None,
                                  'repeat': 1},
                                 {'method': 'GET',
                                  'url': 'http://thebrewery.se/',
                                  'headers': None,
                                  'body': None,
                                  'repeat': 2}])
        self.assertEqual(len(lines.getvalue()), 6)

    def test_multirepeater(self):
        output = Queue()

        def writer(output, *args):

        wrkloadr.multirepeater(2, 3, output.put,
                               [{'method': 'GET',
                                  'url': 'http://thebrewery.se/',
                                  'headers': None,
                                  'body': None,
                                  'repeat': 1},
                                 {'method': 'GET',
                                  'url': 'http://thebrewery.se/',
                                  'headers': None,
                                  'body': None,
                                  'repeat': 2}])

        while True:
            try:
                data = output.get(True, 10)
            except queue.Empty:
                break

