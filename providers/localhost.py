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

import sys

from functools import partial
from multiprocessing import Array

from wrkloadr import multirepeater


class Localhost:

    def __init__(self, output):
        self.output = output
        self.instances = []

    def create_instances(self, instances, wait=None):
        self.instances = ['localhost-%d' % i for i in range(instances)]

    def wait_for_running_instances(self):
        pass

    def remove_instances(self, wait=None):
        self.instances = []

    def wait_for_removed_instances(self):
        pass

    def writer(self, instance, *data):
        csv = ','.join([str(v) for v in data])
        self.output.put(('data', instance, csv))

    def run_single_worker(self, instance, concurrency,
                          repeat, requests):
        multirepeater(concurrency,
                      repeat,
                      partial(self.writer, instance),
                      requests)

    def run_multiple_workers(self, concurrency, repeat, requests):
        self.run_single_worker('localhost',
                               len(self.instances) * concurrency,
                               repeat,
                               requests)
        self.output.put(('status', 'localhost', 'ended'))

    def shutdown(self):
        pass
