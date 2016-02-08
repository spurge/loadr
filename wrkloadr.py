#!/usr/bin/env python3

import click
import csv
import json
import sys

from requests import Request, Session
from re import finditer
from time import time


def millisec():
    return int(round(time() * 1000))


def parseConfigFile(file):
    config = json.loads(file.read(), 'utf-8')
    defaults = {'method': 'GET', 'headers': None, 'body': None}

    for cycle in config:
        for key, val in defaults.items():
            if not key in cycle:
                cycle[key] = val

    return config


def parseConfigCycle(data, history):
    if type(data) is str:
        for match in finditer('{{(.+?)}}', data):
            sys.stdout.write(match.group(1))

        return data

    if type(data) is dict:
        config = {}

        for key, val in data.items():
            config[key] = parseConfigCycle(val, history)

        return config

    return data


def runRequest(cycle, sess, history):
    config = parseConfigCycle(cycle, history)
    req = Request(config['method'],
                  config['url'],
                  headers=config['headers'],
                  data=config['body'])

    try:
        res = sess.send(sess.prepare_request(req))
        contenttype = res.headers['content-type']

        if contenttype == 'application/json' or contenttype == 'text/json':
            res.body = res.json()

        return res
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

    for ci in range(0, cycles):
        history = []

        for cycle in reqs:
            starttime = millisec()
            res = runRequest(cycle, sess, history)
            history += res
            endtime = millisec() - starttime
            writer.writerow([ci,
                             cycle['url'],
                             res.status_code,
                             endtime])


if __name__ == '__main__':
    run()
