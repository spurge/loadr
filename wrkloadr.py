#!/usr/bin/env python3

import click
import csv
import json
import sys

from multiprocessing import Process
from requests import Request, Session
from re import finditer
from time import time


def millisec():
    return int(round(time() * 1000))


def loadconfig(file):
    config = json.loads(file.read(), 'utf-8')
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
                if keys[0] == 'headers':
                    prop = prop.headers
                else:
                    break

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
    config = parseconfig(config, history)
    req = Request(config['method'],
                  config['url'],
                  headers=config['headers'],
                  data=json.dumps(config['body']))

    try:
        return sess.send(sess.prepare_request(req))
    except ConnectionError as e:
        return {'error': 'Connection Error'}


def singlerepeater(repeat, output, config):
    if output != sys.stdout:
        output = open(output, 'a')

    writer = csv.writer(output)

    for ci in range(0, repeat):
        sess = Session()
        history = {}
        ri = 0

        for req in config:
            for rri in range(int(req['repeat'])):
                starttime = millisec()
                res = send(req, sess, history)
                endtime = millisec()
                writer.writerow([ci,
                                 ri,
                                 rri,
                                 res.status_code,
                                 starttime,
                                 endtime])

                history[str(ri)] = res
                ri += 1

                if 'name' in req:
                    history[req['name']] = res


@click.command()
@click.option('-c', '--concurrency', type=int, default=1)
@click.option('-r', '--repeat', type=int, default=1)
@click.option('-o', '--output', type=str, default=sys.stdout)
@click.argument('configfile', type=click.File('r'), default=sys.stdin)
def multirepeater(concurrency, repeat, output, configfile):
    config = loadconfig(configfile)
    processes = [Process(target=singlerepeater,
                         args=(repeat, output, config))
                 for x in range(concurrency)]

    for p in processes:
        p.start()

    for p in processes:
        p.join()

if __name__ == '__main__':
    multirepeater()
