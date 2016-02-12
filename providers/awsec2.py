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


class Awsec2:
    bootscript = """#!/bin/bash
        yum update -y
        yum install -y python34
        curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
        python3 get-pip.py"""

    def __init__(self, config):
        self.ec2 = boto3.resource('ec2')

    def get_instances(self, count):
        self.instances = ec2.create_instances(ImageId=config['ec2-image'],
                                              InstanceType=config['ec2-type'],
                                              MinCount=instances,
                                              MaxCount=instances,
                                              UserData=bootscript)
