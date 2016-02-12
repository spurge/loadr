#!/usr/bin/env python3

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

import providers

def loadconfig(file):
    return json.loads(file.read(), 'utf-8')


def instanciator(provider, instances, concurrency, repeat, output,
                 environments, requests):
    config = loadconfig(environments)
    provider = providers.get_provider(config[provider])
    provider.create_instances(instances)


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
def main(*args, **kwargs):
    instanciator(*args, **kwargs)


if __name__ == '__main__':
    main()
