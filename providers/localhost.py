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

from multiprocessing import Process

from wrkloadr import multirepeater


class Localhost:

    def __init__(self, output):
        self.output = output
        self.instances = []

    def create_instances(self, instances):
        self.instances = range(instances)

    def remove_instances(self):
        self.instances = []

    def create_writer(self, instance):
        def writer(data):
            self.output.put(('data', instance, data))

        return writer

    def run_single_worker(self, instance, concurrency,
                          repeat, requests):
        multirepeater(concurrency,
                      repeat,
                      self.create_writer(instance),
                      requests)

    def run_multiple_workers(self, concurrency, repeat, requests):
        processes = [Process(target=self.run_single_worker,
                             args=(i, concurrency, repeat, requests))
                     for i in self.instances]

        for p in processes:
            p.start()

        for p in processes:
            p.join()

    def shutdown(self):
        pass
