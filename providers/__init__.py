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

    def __init__(self, url, starttime, output):
        self.starttime = starttime
        self.output = output

        parameters = pika.URLParameters(url)

        self.connection = pika.SelectConnection(
            parameters=parameters,
            on_open_callback=self._on_connection_open,
            on_error_callback=self._on_connection_error,
            on_close_callback=self._on_connection_close)

    def _on_connection_open(self, connection):
        self._open_channel()

    def _on_connection_error(self, connection):
        pass

    def _on_connection_close(self, connection):
        pass

    def _on_channel_open(self, channel):
        self._declare_queue()

    def _on_queue_declared(self, channel):
        self._send_starttime()
        self._start_consume()

    def _on_message(self, channel, method, properties, body):
        self.output.put('data', 'messenger', body.decode())

    def _open_channel(self):
        self.channel = self.connection.channel(
            on_open_callback=self._on_channel_open)

    def _declare_queue(self):
        self.channel.declare_queue(
            callback=self._on_queue_declared,
            queue='loadr-signal')

    def _start_consume(self):
        self.channel.basic_consume(
            consumer_callback=self._on_message,
            queue='loadr-data')

    @asyncio.coroutine
    def _wait(self):
        while True:
            yield from asyncio.sleep(1)

    def wait(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._wait())
