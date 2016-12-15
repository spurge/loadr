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

import json
import pika
import sys

from multiprocessing import Process
from requests import Request, Session, ConnectionError
from re import finditer
from time import time, sleep


"""
This is the worker-script that sends requests to specified host by the
request-configuration.

It'll be uploaded to the worker instances, it has hos to work a stand-alone
executable and it must be able to work as a module for testing.

This file contains output writers, a collection of functions to get the
request-sending possible and a executable-routine.
"""


class CsvWriter:
    """An output writer that writes data to stream as csv.
    """

    def __init__(self, stream):
        self.stream = stream

    def wait(self):
        pass

    def write(self, *data):
        self.stream.write(','.join([str(v) for v in data]) + '\n')

    def close(self):
        pass


class RabbitWriter:
    """An output writer that sends data to a RabbitMQ server.
    This is the writer to use when running on a remote instance.
    It'll use the wait method by waiting for a start-signal from the RabbitMQ
    server.
    """

    def __init__(self, url):
        """Connects to RabbitMQ.
        """

        parameters = pika.URLParameters(url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        queue = self.channel.queue_declare()
        self.channel.exchange_declare(exchange='loadr-signal',
                                      exchange_type='fanout')
        self.channel.queue_bind(exchange='loadr-signal',
                                queue=queue.method.queue)

        self.channel.queue_declare(queue='loadr-data')

        self.queue = queue.method.queue

    def wait(self):
        """Wait until there's a start-signal from RabbitMQ server.
        """

        while True:
            method_frame, properties, body = self.channel.basic_get(
                queue=self.queue)

            if body is not None:
                break

            sleep(1)

        self.channel.basic_ack(method_frame.delivery_tag)
        timeout = int(body) - round(millisec() / 1000)

        if timeout > 0:
            sleep(timeout)

    def write(self, *data):
        """Send data to RabbitMQ.
        """

        properties = pika.BasicProperties(content_type='text/plain')
        self.channel.basic_publish(exchange='',
                                   routing_key='loadr-data',
                                   body=','.join([str(v) for v in data]),
                                   properties=properties)

    def close(self):
        """Closes connection to RabbitMQ.
        """

        self.connection.close()


def millisec():
    """Returns a unix timestamp in milliseconds.
    """

    return int(round(time() * 1000))


def configdefaults(config):
    """Setting default data to config and returns it.
    Maybe rewrite this with collections.defaultdict for simplicity.
    """

    defaults = {'method': 'GET',
                'headers': None,
                'body': None,
                'repeat': 1}

    for req in config:
        for key, val in defaults.items():
            if key not in req:
                req[key] = val

    return config


def parseconfig(data, history):
    """Parses request config with history data.
    Takes content with pattern: "{{from(1).json.data}}" and replaces it
    with data from previous requests.
    """

    if type(data) is str:
        for match in finditer('{{from\(([^)]+)\)\.(.+?)}}', data):
            if match.group(1) in history:
                prop = history[match.group(1)]
                keys = match.group(2).split('.')

                if keys[0] == 'json':
                    # JSON data from body
                    prop = prop.json()
                elif keys[0] == 'headers':
                    # Data from headers
                    prop = prop.headers
                else:
                    continue

                for k in keys[1:]:
                    if k in prop:
                        prop = prop[k]
                        continue

                    prop = None
                    break

                if prop is not None:
                    data = data.replace(match.group(0), prop)

        return data

    if type(data) is dict:
        config = {}

        for key, val in data.items():
            config[key] = parseconfig(val, history)

        return config

    return data


def send(config, sess, history):
    """Sends a request specified by config-dict:
    {
        "method": "POST",
        "url": "https://some-host",
        "header": { advanced-session-header-with-content-type },
        "body": { some-data }
    }
    """

    config = parseconfig(config, history)
    req = Request(config['method'],
                  config['url'],
                  headers=config['headers'],
                  data=json.dumps(config['body']))

    return sess.send(sess.prepare_request(req))


def singlerepeater(repeat, writer, config):
    """A request repeater. It runs through the request config x times,
    where x is repeat.

    It'll create a new requests.Session and history record for each repeat.
    """

    out = writer[0](*writer[1:])
    out.wait()

    for ci in range(0, repeat):
        sess = Session()
        history = {}
        ri = 0

        for req in config:
            for rri in range(int(req['repeat'])):
                starttime = millisec()

                try:
                    res = send(req, sess, history)
                    history[str(ri)] = res
                    status = res.status_code
                except ConnectionError as e:
                    status = 'connection-error'

                endtime = millisec()

                out.write(ci,
                          ri,
                          rri,
                          status,
                          starttime,
                          endtime)

                ri += 1

                if 'name' in req:
                    history[req['name']] = res

        sess.close()

    out.close()


def multirepeater(concurrency, repeat, writer, requestconfig):
    """Setting up multiple singlerepeaters by threading for true concurrency.
    """

    config = configdefaults(requestconfig)
    processes = [Process(target=singlerepeater,
                         args=(repeat, writer, config))
                 for x in range(concurrency)]

    for p in processes:
        p.start()

    for p in processes:
        p.join()


if __name__ == '__main__':
    """Stand-alone executable. This is how it is run on the worker instances.
    """

    if len(sys.argv) < 4:
        sys.stderr.write(
            'Too few arguments. 3 required: concurrency, ' +
            'repeat and requests.')
        sys.exit(2)

    if len(sys.argv) > 4:
        # Arguments: rabbitmq url, concurrency, repeat and requests file
        multirepeater(int(sys.argv[2]),
                      int(sys.argv[3]),
                      (RabbitWriter, sys.argv[1]),
                      json.loads(sys.argv[4]))
    else:
        # Arguments: concurrency, repeat and requests file
        multirepeater(int(sys.argv[1]),
                      int(sys.argv[2]),
                      (CsvWriter, sys.stdout.write),
                      json.loads(sys.argv[3]))
