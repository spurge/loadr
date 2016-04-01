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
import pika

from time import time


def get_provider(name, output, **config):
    try:
        exec('from providers.{1} import {0}'
             .format(name, name.lower()))
        provider = locals()[name](**config, output=output)
    except ImportError:
        raise ValueError('No provider with name "{}" in "providers.{}"'
                         .format(name, name.lower()))

    return provider


class Messenger:

    timeout = 60
    last_fetched_time = 0

    def __init__(self, url, starttime, output):
        self.url = url
        self.last_fetched_time = starttime
        self.starttime = starttime
        self.output = output

    @asyncio.coroutine
    def connect(self):
        parameters = pika.URLParameters(self.url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='loadr-signal')
        self.channel.queue_declare(queue='loadr-data')

        self.channel.basic_publish(exchange='',
                                   routing_key='loadr-signal',
                                   body=str(self.starttime))

    @asyncio.coroutine
    def listen(self):
        while True:
            try:
                m, p, b = self.channel.basic_get(queue='loadr-data')

                if b is not None:
                    self.last_fetched_time = time()
                    self.output.put(('data', 'messenger', b.decode()))
                    self.channel.basic_ack(m.delivery_tag)
            except:
                pass

            if self.last_fetched_time + self.timeout < time():
                break

            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def start(self):
        return asyncio.wait([self.connect(),
                             self.listen()])

    def wait(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
