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

import asyncio
import docker
import pika

from multiprocessing import Queue
from time import time, sleep
from unittest import TestCase

from providers import Messenger


class TestMessenger(TestCase):

    def test_messenger(self):
        client = docker.Client(base_url='unix://var/run/docker.sock')
        hostconfig = client.create_host_config(port_bindings={'5672': 5672})
        container = client.create_container(image='rabbitmq:3',
                                            ports=[5672],
                                            host_config=hostconfig)
        cid = container.get('Id')
        client.start(container=cid)
        sleep(10)

        url = 'amqp://localhost:5672/%2F'

        try:
            output = Queue()
            starttime = time() + 10
            messenger = Messenger(url, starttime, output)

            parameters = pika.URLParameters(url)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            queue = channel.queue_declare()
            channel.exchange_declare(exchange='loadr-signal',
                                     exchange_type='fanout')
            channel.queue_bind(exchange='loadr-signal',
                               queue=queue.method.queue)

            channel.queue_declare(queue='loadr-data',
                                  durable=False)

            for i in range(3):
                channel.basic_publish(exchange='',
                                      routing_key='loadr-data',
                                      body='test')

            waiters = [messenger.connect(), messenger.listen()]
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.wait(waiters))

            lines = 0

            m, p, b = channel.basic_get(queue=queue.method.queue)
            self.assertEqual(b.decode(), str(starttime))

            while True:
                try:
                    data = output.get(True, 2)
                except:
                    break

                self.assertEqual(data[0], 'data')
                self.assertEqual(data[2], 'test')
                lines += 1

            self.assertEqual(lines, 3)
        finally:
            client.stop(container=cid)
            client.remove_container(container=cid)
            client.close()
