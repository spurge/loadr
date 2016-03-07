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

import wrkloadr


class HistoryMockup():

    def __init__(self, headers, body):
        self.headers = headers
        self.body = body

    def json(self):
        return self.body


class TestWrkloadr(unittest.TestCase):

    def test_parseconfig(self):
        history = [HistoryMockup({'Content-Type': 'application/json'},
                                 {'some-content': {'subcontent': 'ok'}}),
                   HistoryMockup({'Some-custom-header': 'data'},
                                 {'super-content': '123'})]

        data = {'headers': {
                'custom-header': '{from(0).json.some-content.subcontent} value and {from(1).headers.some-custom-header}'},
               'body': {
                'from-header-0': 'header: {from(0).headers.Content-Type}/stuff',
                'from-body-1': 'body: {from(1).json.super-content}'}}

        parsed = wrkloadr.parseconfig(data, history)

        self.assertEqual(parsed['headers']['custom-header'],
                         'ok value and data')
        self.assertEqual(parsed['body']['from-header-0'],
                         'header: application/json/stuff')
        self.assertEqual(parsed['body']['from-body-1'],
                         'body: 123')
