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
import json
import paramiko
import sys

from io import StringIO
from multiprocessing import Process
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
                            # UserData=self.bootscript,
                            KeyName=self.keypair.name,
                            SecurityGroupIds=[self.securitygroup.id])
        [i.wait_until_running() for i in self.instances]
        [i.load() for i in self.instances]

    def remove_instances(self):
        if self.instances is not None:
            [i.terminate() for i in self.instances]
            [i.wait_until_terminated() for i in self.instances]
            self.instances = None

    def run_instance_worker(self, concurrency, repeat, requests, writer):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        keyfile = StringIO(self.keypair.key_material)
        key = paramiko.RSAKey.from_private_key(keyfile)

        # Retry loop
        for x in range(3):
            try:
                client.connect(i.public_dns_name,
                               username='ec2-user',
                               pkey=key,
                               look_for_keys=False,
                               timeout=60)

                # Upload wrkloadr
                sftp = client.open_sftp()
                sftp.put('wrkloadr.py')

                # Then execute
                channel = client.get_transport().open_session()
                channel.exec_command('python3 wrkloadr.py %d %d \'%s\'' % (
                                        concurrency,
                                        repeat,
                                        json.dumps(requests)))

                stderr = channel.recv_stderr(1024)
                stdout = channel.recv(1024)

                while stderr is not None or stdout is not None:
                    stderr = channel.recv_stderr(1024)
                    stdout = channel.recv(1024)
                    writer.write(stdout)
                    print(stderr)
                    print(stdout)

                channel.close()
                break
            except:
                sleep(60)
            finally:
                if client is not None:
                    client.close()

        keyfile.close()

    def run_workers(self, concurrency, repeat, requests, writer):
        processes = [Process(target=self.run_instance_worker,
                             args=(concurrency, repeat, requests, writer))
                     for i in self.instances]

        for p in processes:
            p.start()

        for p in processes:
            p.join()

    def shutdown(self):
        if self.keypair is not None:
            self.keypair.delete()
            self.keypair = None

        if self.securitygroup is not None:
            self.securitygroup.delete()
            self.securitygroup = None
