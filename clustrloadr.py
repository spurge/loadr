#!/usr/bin/env python3

import boto3
import click
import sys

ec2type = 't2.medium'
ec2image = 

@click.command()
@click.option('-i', '--instances', default=1)
@click.option('-o', '--output', default=sys.stdout)
@click.argument('awsprofile')
def run(instances, output, awsprofile):
    ec2 = boto3.resource('ec2')
    workers = []

    for
    ec2.create_instances

if __name__ == '__main__':
    run()
