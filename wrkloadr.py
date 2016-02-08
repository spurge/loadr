#!/usr/bin/env python3

import click
import csv
import json
import sys

from requests import Request, Session
from time import time


def millisec():
    return int(round(time() * 1000))


def parseConfigFile(file):
    return parseConfigJSON(json.loads(file.read(), 'utf-8'))


def parseConfigJSON(config):
    return config


def parseConfigValue(data, key, history):
    if key in data:
        val = data[key]

        return val

    return None


def runRequest(cycle, sess, history):
    req = Request(cycle['method'],
                  parseConfigValue(cycle, 'url', history),
                  headers=parseConfigValue(cycle, 'headers', history),
                  data=parseConfigValue(cycle, 'body', history))

    try:
        res = sess.send(sess.prepare_request(req))
        type = res.headers['content-type']

        if type == 'application/json' or type == 'text/json':
            return {'data': res.json()}
    except ConnectionError as e:
        return {'error': 'Connection Error'}



@click.command()
@click.option('-c', '--cycles', default=1)
@click.option('-o', '--output', default=sys.stdout)
@click.argument('config', type=click.File('r'), default=sys.stdin)
def run(cycles, output, config):
    if output != sys.stdout:
        output = open(output, 'w')

    writer = csv.writer(output)
    reqs = parseConfigFile(config)
    sess = Session()
    history = None

    for ci in range(0, cycles):
        for cycle in reqs:
            starttime = millisec()
            history = runRequest(cycle, sess, history)
            endtime = millisec() - starttime
            writer.writerow([ci,
                             cycle['url'],
                             endtime])


if __name__ == '__main__':
    run()
