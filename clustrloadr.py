#!/usr/bin/env python3

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
