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


class Messenger:
    """Messenger bridge between provider and it's running instances.
    It's asynchronous and based on RabbitMQ with the pika module.

    When initiated, it requires a starttime. This starttime is sent to the
    RabbitMQ server and will be recieved by the instances as a start-signal for
    a synchronized start.

    Using it async:
        m = Messenger("RabbitMQ-url", time(), Queue())
        await m.connect() # Connects to RabbitMQ and sends start-signal
        await m.listen() # Listens for incoming data and appends it to Queue
                         # Ends then data ends.

    Using it synchronized:
        m = Messenger("RabbitMQ-url", time(), Queue())
        m.wait() # Both connecting and listen. Blocks until incoming data ends.
    """

    # Stop fetching data after timeout from last success.
    timeout = 60
    # When was the last time we got any data.
    last_fetched_time = 0

    def __init__(self, url, starttime, output):
        """
            url = RabbitMQ-url
            starttime = When to start the instances requests,
                        unix timestamp
            output = Queue
        """

        self.url = url
        self.last_fetched_time = starttime
        self.starttime = starttime
        self.output = output

    @asyncio.coroutine
    def connect(self):
        """Asynchronous connection and signal-sender.
        Connects to RabbitMQ-url and sends a start-signal.
        """

        parameters = pika.URLParameters(self.url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange='loadr-signal',
                                      exchange_type='fanout')
        self.channel.queue_declare(queue='loadr-data')

        self.channel.basic_publish(exchange='loadr-signal',
                                   routing_key='',
                                   body=str(self.starttime))

    @asyncio.coroutine
    def listen(self):
        """Asynchronous listens for incoming data.
        When data hasn't been seen since specified timeout - it ends.
        """

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
        """Async waiter for connect and listen methods.
        """

        return asyncio.wait([self.connect(),
                             self.listen()])

    def wait(self):
        """Synchronized wrapper for start().
        """

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
