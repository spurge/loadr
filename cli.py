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

import click
import json
import sys

from multiprocessing import Process, Queue

from clustrloadr import instanciator
from loadr import loadr
from util import config
from wrkloadr import multirepeater


def logger(output):
    while True:
        data = output.get(True)

        if data[0] == 'data':
            sys.stdout.write(data[2])

        if data[0] == 'error':
            sys.stderr.write(data[2])


def wrapper(func, kwargs):
    output = Queue()

    log = Process(target=logger, args=(output))
    stuff = Process(target=func, args={**kwargs, 'output': output})

    log.start()
    stuff.start()

    stuff.join()
    log.join()


@click.command()
@click.option('-c', '--concurrency', type=int, default=1)
@click.option('-r', '--repeat', type=int, default=1)
@click.option('-o', '--output', type=str, default=sys.stdout)
@click.argument('requestfile', type=click.File('r'), default=sys.stdin)
def worker(concurrency, repeat, output, requestfile):
    multirepeater(concurrency, repeat, output,
                  config.load(requestfile))


@click.command()
@click.option('-p', '--provider', type=str)
@click.option('-i', '--instances', type=int, default=1,
              help='Number of instances')
@click.option('-c', '--concurrency', type=int, default=1,
              help='Concurrency per instance')
@click.option('-r', '--repeat', type=int, default=1)
@click.option('-o', '--output', type=str, default=sys.stdout)
@click.option('-e', '--environments', type=click.File('r'),
              help='Environments configuration file')
@click.option('-q', '--requests', type=click.File('r'),
              help='Requests configuration file')
def cluster(provider, instances, concurrency, repeat,
              output, environments, requests):
    instanciator(instances, concurrency, repeat, output,
                 config.load(environments)[provider],
                 config.load(requests))


@click.command()
@click.option('-e', '--environments', type=click.File('r'),
              help='Environments configuration file')
@click.option('-q', '--requests', type=click.File('r'),
              help='Requests configuration file')
@click.argument('sessionfile', type=click.File('r'), default=sys.stdin)
def main(environments, requests, sessionfile):
    loadr(config.load(environments), config.load(requests),
          config.load(sessionfile))
