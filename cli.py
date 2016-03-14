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

from clustrloadr import Session
from loadr import Loadr
from util import config
from wrkloadr import multirepeater, csvwriter


@click.command()
@click.option('-c', '--concurrency', type=int, default=1,
              help='How many concurrent requests to send')
@click.option('-r', '--repeat', type=int, default=1,
              help='How many times to repeat the whole requests cycle')
@click.argument('requestfile', type=click.File('r'), default=sys.stdin,
                help='Requests cycle configuration json file')
def worker(concurrency, repeat, requestfile):
    multirepeater(concurrency, repeat, csvwriter(sys.stdout.write),
                  config.load(requestfile))


@click.command()
@click.option('-p', '--provider', type=str,
              help='Which provider to use from the environment config json file')
@click.option('-i', '--instances', type=int, default=1,
              help='Number of instances to run at the provider')
@click.option('-c', '--concurrency', type=int, default=1,
              help='How many concurrent requests per instance')
@click.option('-r', '--repeat', type=int, default=1,
              help='How many times to repeat the whole requests cycle')
@click.option('-e', '--environments', type=click.File('r'),
              help='Environments configuration json file')
@click.option('-q', '--requests', type=click.File('r'),
              help='Requests cycle configuration json file')
def cluster(provider, instances, concurrency, repeat,
            output, environments, requests):
    loadr = Loadr()
    loadr.ui('Csv')
    loadr.providers(config.load(environments))
    loadr.requests(config.load(requests))
    loadr.start({'provider': provider,
                   'instances': instances,
                   'concurrency': concurrency,
                   'repeat': repeat})

@click.command()
@click.option('-s', '--session', type=click.File('r'),
              help='Session configuration json file')
@click.option('-e', '--environments', type=click.File('r'),
              help='Environments configuration json file')
@click.option('-q', '--requests', type=click.File('r'),
              help='Requests cycle configuration json file')
@click.option('-u', '--ui', type=str, default='Csv',
              help='Which ui to use')
def main(session, environments, requests, ui):
    loadr = Loadr()
    loadr.ui(ui)
    loadr.providers(config.load(environments))
    loadr.requests(config.load(requests))
