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

import docker
import json
import pika
import sys

from io import StringIO
from multiprocessing import Value
from requests import Response, Session
from time import sleep
from unittest import TestCase

import wrkloadr


class HistoryMockup:

    def __init__(self, headers, body):
        self.headers = headers
        self.body = body

    def json(self):
        return self.body


class TestWriter:

    def __init__(self, test, lines):
        self.test = test
        self.lines = lines

    def wait(self):
        pass

    def write(self, *args):
        self.lines.value += 1
        self.test.assertEqual(len(args), 6)
        sys.stdout.write('')

        for val in args:
            self.test.assertIsInstance(val, int)

    def close(self):
        pass


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
        lines = Value('i', 0)

        wrkloadr.singlerepeater(2,
                                (TestWriter, self, lines),
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

        self.assertEqual(lines.value, 6)

    def test_multirepeater(self):
        lines = Value('i', 0)

        wrkloadr.multirepeater(2, 3, (TestWriter, self, lines),
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

        self.assertEqual(lines.value, 18)


    def test_csvwriter(self):
        stream = StringIO()

        csv = wrkloadr.CsvWriter(stream)
        csv.wait()
        csv.write(*range(3))
        csv.close()

        self.assertEqual(stream.getvalue(), '0,1,2\n')

    def test_rabbitwriter(self):
        client = docker.Client(base_url='unix://var/run/docker.sock')
        hostconfig = client.create_host_config(port_bindings={'5672':5672})
        container = client.create_container(image='rabbitmq:3',
                                            ports=[5672],
                                            host_config=hostconfig)
        cid = container.get('Id')
        client.start(container=cid)
        sleep(10)

        url = 'amqp://localhost:5672/%2F'

        try:
            parameters = pika.URLParameters(url)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue='loadr-signal',
                                  durable=False)
            properties = pika.BasicProperties(content_type='text/plain')
            channel.basic_publish(exchange='',
                                  routing_key='loadr-signal',
                                  body=str(round(wrkloadr.millisec() / 1000) + 2))

            rabbit = wrkloadr.RabbitWriter(url)
            rabbit.wait()
            rabbit.write(*range(3))
            rabbit.close()

            method_frame, properties, body = channel.basic_get(queue='loadr-data')

            self.assertEqual(body.decode(), '0,1,2')

            connection.close()
        finally:
            client.stop(container=cid)
            client.remove_container(container=cid)
            client.close()

