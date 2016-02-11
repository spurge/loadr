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

import boto3
import click
import json
import sys


def loadconfig(file):
    return json.loads(file.read(), 'utf-8')


def getawsec2(config, count):
    bootscript = """#!/bin/bash
yum update -y
yum install -y python34
curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
python3 get-pip.py"""

    ec2 = boto3.resource('ec2')
    return ec2.create_instances(ImageId=config['ec2-image'],
                                InstanceType=config['ec2-type'],
                                MinCount=count,
                                MaxCount=count,
                                UserData=bootscript)


def getinstances(*args):
    if config['type'] == 'aws-ec2':
        return getawsec2(*args)

    return None


@click.command()
@click.option('-i', '--instances', type=int, default=1,
              help='Number of instances')
@click.option('-c', '--concurrency', type=int, default=1,
              help='Concurrency per instance')
@click.option('-r', '--repeat', type=int, default=1)
@click.option('-o', '--output', type=str, default=sys.stdout)
@click.option('-e', '--environment', type=click.File('r'),
              help='Environment configuration file')
@click.option('-q', '--requests', type=click.File('r'),
              help='Requests configuration file')
def instanciator(instances, concurrency, repeat, output,
                 environment, requests):
    config = loadconfig(environment)
    runners = getinstances(config, instances)


if __name__ == '__main__':
    instanciator()
