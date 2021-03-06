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

import asyncio
import boto3
import json
import math
import paramiko
import pika
import sys

from io import StringIO
from multiprocessing import get_context, Queue
from time import time, sleep

from util import random_string
from providers import Messenger


class Awsec2:
    """Creates EC2 instances at AWS and then runs workers in these instances.
    It'll create one RabbitMQ instance per x worker instances. The RabbitMQ
    instances are controlled by the Messenger-class. They'll sends a
    start-signal to the workers and recieves incoming data.
    """

    # How many worker instances per RabbitMQ
    instances_per_messenger = 20
    # How many simultaneous ssh connections for setting up the environments.
    concurrent_ssh_sessions = 10
    # How many times to retry the ssh connections before giving up.
    ssh_retries = 10
    # How long to wait before next ssh connection retry.
    ssh_retry_timeout = 10
    # When to give up connection if no response.
    ssh_timeout = 60
    # How long to wait before instances are ready after bootstrapping.
    bootscript_wait_timeout = 60

    # RabbitMQ AWS EC2 image id
    messengers_image_id = 'ami-e2df388d'
    # RabbitMQ AWS EC2 instance type
    messengers_type = 't2.medium'
    # RabbitMQ randomized username - created when messenger instance is created.
    messengers_username = ''
    # RabbitMQ randomized password - created when messenger instance is created.
    messengers_password = ''
    # RabbitMQ bootstrap script. Installs RabbitMQ and starts it.
    messengers_bootscript = """#!/bin/bash
yum update -y
wget http://www.rabbitmq.com/releases/erlang/erlang-18.3-1.el6.x86_64.rpm
yum install -y erlang-18.3-1.el6.x86_64.rpm
wget http://www.rabbitmq.com/releases/rabbitmq-server/v3.6.1/rabbitmq-server-3.6.1-1.noarch.rpm
rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
yum install -y rabbitmq-server-3.6.1-1.noarch.rpm
chkconfig rabbitmq-server on
service rabbitmq-server start
rabbitmqctl add_user {username} {password}
rabbitmqctl set_permissions {username} ".*" ".*" ".*"
"""

    # Worker bootstrap script. Installs python 3.4 with pika and requests modules
    workers_bootscript = """#!/bin/bash
yum update -y
yum install -y python34 python34-pip
alternatives --set python /usr/bin/python3.4
pip install pika requests
"""

    def __init__(self, output, image_id, instance_type, **kwargs):
        # All output in a single queue
        self.output = output

        # Save these for later -> create_instances
        self.image_id, self.instance_type = image_id, instance_type

        self.session = self.create_session(**kwargs)
        self.ec2 = self.session.resource('ec2')
        self.keypair = self.create_keypair()
        self.messengers_securitygroup = self.create_messengers_securitygroup()
        self.workers_securitygroup = self.create_workers_securitygroup()

        self.messengers_username = random_string(16)
        self.messengers_password = random_string(16)

        self.messengers = []
        self.instances = []

    def get_messenger_url(self, messenger):
        """Returns an URL to a RabbitMQ messenger by username, password,
        and public dns name.
        """

        url = 'amqp://{}:{}@{}:5672/%2F'.format(
            self.messengers_username,
            self.messengers_password,
            messenger.public_dns_name)
        print(url + "\n")
        return url

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

    def create_messengers_securitygroup(self):
        """Creates a security policy which makes rabbitmq reachable
        """

        sgname = 'loadr-messenger-%s' % random_string()
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
                                                Description='loadr rabbitmq messenger access')
            sg.authorize_ingress(IpProtocol='tcp',
                                 CidrIp='0.0.0.0/0',
                                 FromPort=5672,
                                 ToPort=5672)

        return sg


    def create_workers_securitygroup(self):
        """Creates a security policy which makes a ssh access possible
        """

        sgname = 'loadr-worker-%s' % random_string()
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

        messengers_count = math.ceil(instances / self.instances_per_messenger)

        self.messengers = self.ec2.create_instances(
                            ImageId=self.messengers_image_id,
                            InstanceType=self.messengers_type,
                            MinCount=messengers_count,
                            MaxCount=messengers_count,
                            UserData=self.messengers_bootscript.format(
                                username=self.messengers_username,
                                password=self.messengers_password),
                            SecurityGroupIds=[self.messengers_securitygroup.id])

        self.instances = self.ec2.create_instances(
                            ImageId=self.image_id,
                            InstanceType=self.instance_type,
                            MinCount=instances,
                            MaxCount=instances,
                            UserData=self.workers_bootscript,
                            KeyName=self.keypair.name,
                            SecurityGroupIds=[self.workers_securitygroup.id])

        if wait:
            self.wait_for_running_instances()

    def wait_for_running_instances(self):
        """Blocks current thread until all instances are running.
        This method must be thread-safe.
        """

        for i in self.messengers + self.instances:
            i.wait_until_running()
            sleep(self.bootscript_wait_timeout)
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
            self.get_messenger_url(messenger),
            concurrency,
            repeat,
            json.dumps(requests)))
        self.output.put(('status', instance.id, 'running command'))

        # Close and quit
        client.close()
        keyfile.close()

    def run_multiple_workers(self, concurrency, repeat, requests, starttime):
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

        # This is not correct!
        # Rewrite this!

        for i in range(0, self.concurrent_ssh_sessions - 1):
            # Start processes
            for p in processes[i * self.concurrent_ssh_sessions:]:
                p.start()

            # Then wait for all processes to end
            for p in processes[i * self.concurrent_ssh_sessions:]:
                p.join()

        # Define a start time
        starttime = int(round(time() + 70))
        sleep(60)

        waiters = []

        # Collect and redirect data
        for messenger in self.messengers:
            # Get all the necessary data for the instance,
            # like IP and dns name.
            # Even if this was done in run_single_repeater - it was done in
            # another thread, and the data isn't accessable here.
            messenger.wait_until_running()
            messenger.load()

            # Send a run messege to all messengers
            # and start receiving data from all messengers
            broker = Messenger(self.get_messenger_url(messenger),
                               starttime,
                               self.output)
            waiters.append(broker.connect())
            waiters.append(broker.listen())

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(waiters))

    def shutdown(self):
        """Deletes keys and policies.
        """

        if self.keypair is not None:
            self.keypair.delete()
            self.keypair = None

        if self.workers_securitygroup is not None:
            self.workers_securitygroup.delete()
            self.workers_securitygroup = None


        if self.messengers_securitygroup is not None:
            self.messengers_securitygroup.delete()
            self.messengers_securitygroup = None
