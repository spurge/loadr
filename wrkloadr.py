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
import sys

from multiprocessing import Process, Queue
from requests import Request, Session, ConnectionError
from re import finditer
from time import time


def millisec():
    return int(round(time() * 1000))


def configdefaults(config):
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
    if type(data) is str:
        for match in finditer('{{from\(([^)]+)\)\.(.+?)}}', data):
            if match.group(1) in history:
                prop = history[match.group(1)]
                keys = match.group(2).split('.')

                if keys[0] == 'json':
                    prop = prop.json()
                elif keys[0] == 'headers':
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


def csvwriter(output, *xtra):
    def writer(*data):
        output(','.join([str(v) for v in data + xtra]) + '\n')

    return writer


def send(config, sess, history):
    config = parseconfig(config, history)
    req = Request(config['method'],
                  config['url'],
                  headers=config['headers'],
                  data=json.dumps(config['body']))

    return sess.send(sess.prepare_request(req))


def singlerepeater(repeat, writer, config):
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

                writer(ci,
                       ri,
                       rri,
                       status,
                       starttime,
                       endtime)

                ri += 1

                if 'name' in req:
                    history[req['name']] = res


def multirepeater(concurrency, repeat, writer, requestconfig):
    config = configdefaults(requestconfig)
    processes = [Process(target=singlerepeater,
                         args=(repeat, writer, config))
                 for x in range(concurrency)]

    for p in processes:
        p.start()

    for p in processes:
        p.join()


if __name__ == '__main__':
    import json

    if len(sys.argv) < 4:
        sys.stderr.write('Too few arguments. 3 required: concurrency, repeat and requests.')
        sys.exit(2)

    writer = csvwriter(sys.stdout.write)

    multirepeater(int(sys.argv[1]),
                  int(sys.argv[2]),
                  writer,
                  json.loads(sys.argv[3]))
