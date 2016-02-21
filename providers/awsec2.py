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
import paramiko
import sys

from io import StringIO
from time import sleep


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
        self.securitygroup = self.create_securitygroup()
        self.instances = []

    def create_keypair(self):
        keypair = self.ec2.KeyPair('loadr')
        keypair.delete()
        return self.ec2.create_key_pair(KeyName='loadr')

    def create_securitygroup(self):
        sg = None

        for vpc in self.ec2.vpcs.all():
            if sg is not None:
                break

            for group in vpc.security_groups.all():
                if group.group_name == 'loadr':
                    sg = group
                    break

        if sg is None:
            sg = self.ec2.create_security_group(GroupName='loadr',
                                                Description='loadr ssh access')
            sg.authorize_ingress(IpProtocol='tcp',
                                 CidrIp='0.0.0.0/0',
                                 FromPort=22,
                                 ToPort=22)

        return sg


    def create_instances(self, instances):
        self.instances = self.ec2.create_instances(
                            ImageId=self.config['image'],
                            InstanceType=self.config['type'],
                            MinCount=instances,
                            MaxCount=instances,
                            UserData=self.bootscript,
                            KeyName=self.keypair.name,
                            SecurityGroupIds=[self.securitygroup.id])
        [i.wait_until_running() for i in self.instances]
        [i.load() for i in self.instances]

    def remove_instances(self):
        if self.instances is not None:
            [i.terminate() for i in self.instances]
            [i.wait_until_terminated() for i in self.instances]
            self.instances = None

    def run_worker(self, requests, writer):
        for i in self.instances:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            keyfile = StringIO(self.keypair.key_material)
            key = paramiko.RSAKey.from_private_key(keyfile)

            for x in range(3):
                try:
                    client.connect(i.public_dns_name,
                                   username='ec2-user',
                                   pkey=key,
                                   look_for_keys=False,
                                   timeout=60)
                    stdin, stdout, stderr = client.exec_command('ls -lah')

                    for l in stdout:
                        writer.write(l)

                    stdin.close()
                    stdout.close()
                    stderr.close()
                    break
                except:
                    sleep(60)

            client.close()
            keyfile.close()

    def shutdown(self):
        if self.keypair is not None:
            self.keypair.delete()
            self.keypair = None

        if self.securitygroup is not None:
            self.securitygroup.delete()
            self.securitygroup = None
