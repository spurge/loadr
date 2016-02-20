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
import sys

from paramiko import SSHClient


class Awsec2:
    bootscript = """#!/bin/bash
        yum update -y
        yum install -y python34
        curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
        python3 get-pip.py"""

    def __init__(self, config):
        self.session = boto3.session.Session(profile_name=config['profile'],
                                             region_name=config['region'])
        self.ec2 = self.session.resource('ec2')
        self.config = config
        self.keypair = self.create_keypair()
        self.instances = []

    def create_keypair(self):
        keypair = self.ec2.KeyPair('loadr')
        keypair.delete()

        return self.ec2.create_key_pair(KeyName='loadr')

    def create_instances(self, instances):
        self.instances = self.ec2.create_instances(
                            ImageId=self.config['image'],
                            InstanceType=self.config['type'],
                            MinCount=instances,
                            MaxCount=instances,
                            UserData=self.bootscript,
                            KeyName='loadr')
        [i.wait_until_running() for i in self.instances]

    def remove_instances(self):
        [i.terminate() for i in self.instances]
        self.keypair.delete()

    def run_worker(self, requests):
        for i in self.instances:
            client = SSHClient()
            client.connect(i.public_ip_address, pkey=self.keypair.key_material)
            stdin, stdout, stderr = client.exec_command('ls -lh')
            print(stdin)
            print(stdout)
            print(stderr)

    def shutdown(self):
        # self.ec2.meta.client.close()
        pass
