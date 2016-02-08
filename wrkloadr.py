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


def loadconfig(file):
    config = json.loads(file.read(), 'utf-8')
    defaults = {'method': 'GET',
                'headers': None,
                'body': None}

    for req in config:
        for key, val in defaults.items():
            if not key in req:
                req[key] = val

    return config


def parseconfig(data, history):
    if type(data) is str:
        for match in finditer('{{from\(([^)]+)\)\.(.+?)}}', data):
            if match.group(1) in history:
                prop = history[match.group(1)]
                keys = match.group(2).split('.')

                if keys[0] == 'body':
                    prop = prop.body
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

                if prop != None:
                    data = data.replace(match.group(0), prop)

        return data

    if type(data) is dict:
        config = {}

        for key, val in data.items():
            config[key] = parseconfig(val, history)

        return config

    return data


def runRequest(config, sess, history):
    config = parseconfig(config, history)
    req = Request(config['method'],
                  config['url'],
                  headers=config['headers'],
                  data=json.dumps(config['body']))

    try:
        res = sess.send(sess.prepare_request(req))
        contenttype = res.headers['content-type']

        if contenttype[:16] == 'application/json':
            res.body = res.json()

        return res
    except ConnectionError as e:
        return {'error': 'Connection Error'}



@click.command()
@click.option('-c', '--cycles', default=1)
@click.option('-o', '--output', default=sys.stdout)
@click.argument('configfile', type=click.File('r'), default=sys.stdin)
def run(cycles, output, configfile):
    if output != sys.stdout:
        output = open(output, 'w')

    writer = csv.writer(output)
    config = loadconfig(configfile)

    for ci in range(0, cycles):
        sess = Session()
        history = {}
        ri = 0

        for req in config:
            starttime = millisec()
            res = runRequest(req, sess, history)
            endtime = millisec() - starttime
            writer.writerow([ci,
                             req['url'],
                             res.status_code,
                             endtime])

            history[str(ri)] = res
            ri += 1

            if 'name' in req:
                history[req['name']] = res


if __name__ == '__main__':
    run()
