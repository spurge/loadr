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
    """Creates EC2 instances at AWS
    and then either runs workers in these instances,
    or create nested instances and proxies their output.

    The nested instances-stuff is not implemented yet.
    """

    def __init__(self, image_id, instance_type, **kwargs):
        # Save these for later -> create_instances
        self.image_id, self.instance_type = image_id, instance_type

        self.session = self.create_session(**kwargs)
        self.ec2 = self.session.resource('ec2')
        self.keypair = self.create_keypair()
        self.securitygroup = self.create_securitygroup()

        self.instances = []

    def create_session(self, region, profile=None,
                       access_key=None, secret_key=None):
        """Logs in into aws with either a profile with matching credentials,
        or access_key/secret_key combo.
        """

        if profile is not None:
            return boto3.session.Session(profile_name=profile,
                                         region_name=region)
        elif access_key is not None and secret_key is not None:
            return boto3.session.Session(aws_access_key_id=access_key,
                                         aws_secret_access_key=secret_key,
                                         region_name=region)

        raise ValueError('Either profile or access_key/secret_key has to be set')

    def create_keypair(self):
        """Creates a rsa key pair for ssh access
        """

        keypair = self.ec2.KeyPair('loadr')
        keypair.delete()
        return self.ec2.create_key_pair(KeyName='loadr')

    def create_securitygroup(self):
        """Creates a security policy which makes a ssh access possible
        """

        sg = None

        # Look for existing security group
        for vpc in self.ec2.vpcs.all():
            if sg is not None:
                break

            for group in vpc.security_groups.all():
                if group.group_name == 'loadr':
                    sg = group
                    break

        # Create one if non-existent
        if sg is None:
            sg = self.ec2.create_security_group(GroupName='loadr',
                                                Description='loadr ssh access')
            sg.authorize_ingress(IpProtocol='tcp',
                                 CidrIp='0.0.0.0/0',
                                 FromPort=22,
                                 ToPort=22)

        return sg

    def create_instances(self, instances):
        """Creates x number of instances.
        Instance type and image where defined in the class __init__.
        """

        self.instances = self.ec2.create_instances(
                            ImageId=self.image_id,
                            InstanceType=self.instance_type,
                            MinCount=instances,
                            MaxCount=instances,
                            KeyName=self.keypair.name,
                            SecurityGroupIds=[self.securitygroup.id])

        # Then wait for them all to be ready
        for i in self.instances:
            i.wait_until_running()
            i.load()

    def remove_instances(self):
        """Terminates all instances.
        """

        for i in self.instances:
            i.terminate()
            i.wait_until_terminated()

        self.instances = []

    def run_single_worker(self, instance, concurrency,
                          repeat, requests, writer):
        """Creates a ssh connection to specified instance,
        uploads wrkloadr.py and runs it. It will the write all stdout to
        specified writer.
        Used by the run_multiple_workers method.
        """

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        keyfile = StringIO(self.keypair.key_material)
        key = paramiko.RSAKey.from_private_key(keyfile)

        # Number of retries
        retries = 3

        # Retry loop
        for r in range(retries):
            # It will take at least 60 seconds before the server is responding
            sleep(60)

            try:
                client.connect(instance.public_dns_name,
                               username='ec2-user',
                               pkey=key,
                               look_for_keys=False,
                               timeout=60)
                break
            except:
                if r == retries - 1:
                    raise

        # Upload wrkloadr
        sftp = client.open_sftp()
        sftp.put('wrkloadr.py', 'wrkloadr.py')

        # Then execute
        channel = client.get_transport().open_session()
        channel.exec_command('python3 wrkloadr.py {} {} \'{}\''.format(
                                concurrency,
                                repeat,
                                json.dumps(requests)))

        # Write all stdout from ssh channel to specified writer
        while not channel.exit_status_ready():
            stdout = channel.recv(1024)
            stdout_str = stdout.decode('utf-8').strip()

            if len(stdout_str) > 0:
                sys.stdout.write(stdout_str)

            writer.write(stdout_str)

        # Close and quit
        channel.close()
        client.close()
        keyfile.close()

    def run_multiple_workers(self, concurrency, repeat, requests, writer):
        """Runs multiple workers on each instance.
        Each worker within its own thread.
        Used run_single_worker method.
        """

        processes = [Process(target=self.run_single_worker,
                             args=(i, concurrency, repeat, requests, writer))
                     for i in self.instances]

        for p in processes:
            p.start()

        for p in processes:
            p.join()

    def shutdown(self):
        """Deletes keys and policies.
        """

        if self.keypair is not None:
            self.keypair.delete()
            self.keypair = None

        if self.securitygroup is not None:
            self.securitygroup.delete()
            self.securitygroup = None
