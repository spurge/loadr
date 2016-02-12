#!/bin/env python3

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

from clustrloadr import instanciator


def loadconfig(file):
    return json.loads(file.read(), 'utf-8')


def loadr(environments, requests, sessionconfig):
    sessions = loadconfig(sessionconfig)

    for s in sessions:
        instanciator(s['environment'], s['instances'], s['concurrency'],
                     s['repeat'], sys.stdout, environments, requests)


@click.command()
@click.option('-e', '--environments', type=click.File('r'),
              help='Environments configuration file')
@click.option('-q', '--requests', type=click.File('r'),
              help='Requests configuration file')
@click.argument('sessionconfig', type=click.File('r'), default=sys.stdin)
def main(*args, **kwargs):
    loadr(*args, **kwargs)


if __name__ == '__main__':
    main()
