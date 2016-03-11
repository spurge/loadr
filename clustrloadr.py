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

from multiprocessing import get_context, Pipe

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
        self._providers = {}
        self._requests = []
        self._session = []
        self.output = output

    def add_provider(self, name, provider_type, **config):
        self._providers[name] = Provider(provider_type,
                                         self.output,
                                         **config)

    def providers(self, providers=[]):
        for name, config in providers.items():
            provider_type = config['type']
            self.add_provider(name,
                              provider_type,
                              **{key: val
                                 for key, val
                                 in config.items()
                                 if key != 'type'})

        return self._providers

    def requests(self, requests=None):
        if requests is not None:
            self._requests = requests

        return self._requests

    def start(self, config=[]):
        self._session = config
        processes = []
        mp = get_context('fork')

        def startwrapper(provider, instances, pipe):
            provider.start(instances)
            pipe.send(provider.provider.instances)
            pipe.close()

        for s in self._session:
            parent, child = Pipe()
            provider = self._providers[s['provider']]
            process = mp.Process(target=startwrapper,
                                 args=(provider,
                                       s['instances'],
                                       child))
            process.start()
            processes += [(provider, process, parent)]

        for (provider, process, pipe) in processes:
            provider.provider.instances = pipe.recv()
            process.join()

    def stop(self):
        for provider in self._providers.values():
            provider.stop()

    def run(self):
        processes = []
        mp = get_context('fork')

        for s in self._session:
            provider = self._providers[s['provider']]
            process = mp.Process(target=provider.run,
                                 args=(s['concurrency'],
                                       s['repeat'],
                                       self._requests))
            processes += [process]

        for p in processes:
            p.start()

        for p in processes:
            p.join()
