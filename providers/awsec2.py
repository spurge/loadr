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
import math
import paramiko
import sys

from io import StringIO
from multiprocessing import get_context, Queue
from time import sleep

from util import random_string


class Awsec2:
    """Creates EC2 instances at AWS
    and then either runs workers in these instances,
    or create nested instances and proxies their output.

    The nested instances-stuff is not implemented yet.
    """

    instances_per_messenger = 20
    concurrent_ssh_sessions = 10
    ssh_retries = 10
    ssh_retry_timeout = 10
    ssh_timeout = 60
    bootscript_wait_timeout = 60

    messengers_image_id = 'ami-e2df388d'
    messengers_type = 't2.medium'
    messengers_bootscript = """#!/bin/bash
yum update -y
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
wget http://rpms.famillecollet.com/enterprise/remi-release-6.rpm
sudo rpm -Uvh remi-release-6*.rpm epel-release-6*.rpm
yum install -y erlang
wget http://www.rabbitmq.com/releases/rabbitmq-server/v3.6.1/rabbitmq-server-3.6.1-1.noarch.rpm
rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
yum install -y rabbitmq-server-3.6.1-1.noarch.rpm
chkconfig rabbitmq-server on
service rabbitmq-server start
"""

    workers_bootscript = """#!/bin/bash
yum update -y
yum install -y python34 python34-pip
alternatives --set python /usr/bin/python3.4
pip install pika requests
"""
    """Lines of bash that will run when the workers instances initializes
    """


    def __init__(self, output, image_id, instance_type, **kwargs):
        # All output in a single queue
        self.output = output

        # Save these for later -> create_instances
        self.image_id, self.instance_type = image_id, instance_type

        self.session = self.create_session(**kwargs)
        self.ec2 = self.session.resource('ec2')
        self.keypair = self.create_keypair()
        self.securitygroup = self.create_securitygroup()

        self.messengers = []
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

        keyname = 'loadr-%s' % random_string()
        keypair = self.ec2.KeyPair(keyname)
        keypair.delete()
        return self.ec2.create_key_pair(KeyName=keyname)

    def create_securitygroup(self):
        """Creates a security policy which makes a ssh access possible
        """

        sgname = 'loadr-%s' % random_string()
        sg = None

        # Look for existing security group
        for vpc in self.ec2.vpcs.all():
            if sg is not None:
                break

            for group in vpc.security_groups.all():
                if group.group_name == sgname:
                    sg = group
                    break

        # Create one if non-existent
        if sg is None:
            sg = self.ec2.create_security_group(GroupName=sgname,
                                                Description='loadr ssh access')
            sg.authorize_ingress(IpProtocol='tcp',
                                 CidrIp='0.0.0.0/0',
                                 FromPort=22,
                                 ToPort=22)

        return sg

    def create_instances(self, instances, wait=True):
        """Creates x number of instances.
        Instance type and image where defined in the class __init__.
        This method is not thread-safe!
        """

        self.output.put(('status', 'awsec2', 'creating instances'))

        messenger_count = math.ceil(instances / self.instances_per_messenger)

        self.messengers = self.ec2.create_instances(
                            ImageId=self.messenger_image_id,
                            InstanceType=self.messenger_type,
                            MinCount=messenger_count,
                            MaxCount=messenger_count,
                            UserData=self.messengers_bootscript)

        self.instances = self.ec2.create_instances(
                            ImageId=self.image_id,
                            InstanceType=self.instance_type,
                            MinCount=instances,
                            MaxCount=instances,
                            UserData=self.workers_bootscript,
                            KeyName=self.keypair.name,
                            SecurityGroupIds=[self.securitygroup.id])

        if wait:
            self.wait_for_running_instances()

    def wait_for_running_instances(self):
        """Blocks current thread until all instances are running.
        This method must be thread-safe.
        """

        for i in self.messengers + self.instances:
            i.wait_until_running()
            sleep(self.bootscript_timeout)
            self.output.put(('status', i.id, 'running'))

    def remove_instances(self, wait=True):
        """Terminates all instances.
        This method is not thread-safe.
        """

        for i in self.messengers + self.instances:
            i.terminate()

        if wait:
            self.wait_for_removed_instances()

    def wait_for_removed_instances(self):
        """Blocks current thread until all instances are terminated.
        This method must be thread-safe.
        """

        for i in self.messengers + self.instances:
            i.wait_until_terminated()
            self.output.put(('status', i.id, 'removed'))

        self.instances = []

    def run_single_worker(self, instance, messenger,
                          concurrency, repeat, requests):
        """Creates a ssh connection to specified instance,
        uploads wrkloadr.py and runs it. It will the write all stdout to
        specified writer.
        Used by the run_multiple_workers method.
        """

        self.output.put(('status', instance.id, 'connecting'))

        # Get all the necessary data for the instance,
        # like IP and dns name.
        messenger.wait_until_running()
        messenger.load()
        instance.wait_until_running()
        instance.load()

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        keyfile = StringIO(self.keypair.key_material)
        key = paramiko.RSAKey.from_private_key(keyfile)

        # Retry loop
        for r in range(self.ssh_retries):
            # It will take at least 60 seconds before the server is responding
            sleep(self.ssh_retry_timeout)

            try:
                client.connect(instance.public_dns_name,
                               username='ec2-user',
                               pkey=key,
                               look_for_keys=False,
                               timeout=self.ssh_timeout)
                self.output.put(('status', instance.id, 'connected'))
                break
            except:
                if r == retries - 1:
                    raise

        # Upload wrkloadr
        sftp = client.open_sftp()
        sftp.put('wrkloadr.py', 'wrkloadr.py')

        # Then execute
        client.exec_command('sh -c "python wrkloadr.py \'{}\' {} {} \'{}\' & echo $!"'.format(
                            messenger.private_dns_name,
                            concurrency,
                            repeat,
                            json.dumps(requests)))
        self.output.put(('status', instance.id, 'running command'))

        # Close and quit
        client.close()
        keyfile.close()

    def run_multiple_workers(self, concurrency, repeat, requests):
        """Runs multiple workers on each instance.
        Each worker within its own thread.
        Used run_single_worker method.
        """

        # Initialize the instance processes
        mp = get_context('fork')
        processes = []

        for i, messenger in enumerate(self.messengers):
            for instance in self.instances[i * self.instances_per_messenger:]:
                processes.append(mp.Process(target=self.run_single_worker,
                                            args=(instance, messenger,
                                                  concurrency, repeat, requests)))

        for i in range(0, self.concurrent_ssh_sessions - 1):
            # Start processes
            for p in processes[i * self.concurrent_ssh_sessions:]:
                p.start()

            # Then wait for all processes to end
            for p in processes[i * self.concurrent_ssh_sessions:]:
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
