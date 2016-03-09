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

from multiprocessing import Process, Queue

class Provider:

    def __init__(self, name, output, **config):
        try:
            exec('from providers.{1} import {0}'
                 .format(name, name.lower()))

            self.provider = locals()[name](**config, output=output)
        except ImportError:
            raise ValueError('No provider with name "{}" in "providers.{}"'
                             .format(name, name.lower()))

    def start(self, instances):
        self.provider.create_instances(instances)

    def stop(self):
        self.provider.remove_instances()
        self.provider.shutdown()

    def run(self, concurrency, repeat, requests):
        self.provider.run_multiple_workers(concurrency,
                                           repeat,
                                           requests)


class Session:

    def __init__(self, output):
        self.providers = []
        self.output = output

    def add_provider(self, name, concurrency, repeat, **config):
        self.providers += {'concurrency': concurrency,
                           'provider': Provider(name,
                                                self.output,
                                                **config)}

    def start(self):
        pass


def sessionizer(session, requests, output):
    """Runs multple instanciators defined by session.
    """

    processes = [Process(target=instanciator,
                         args={'requests': requests,
                               'output': output} + session)
                 for s in session]

    for p in processes:
        p.start()

    for p in processes:
        p.join()
