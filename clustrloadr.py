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

from multiprocessing import get_context

from providers import get_provider


class Session:

    def __init__(self, output):
        self._providers = {}
        self._requests = []
        self._session = []
        self.output = output

    def add_provider(self, name, provider_type, **config):
        self._providers[name] = get_provider(provider_type,
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

        for s in self._session:
            provider = self._providers[s['provider']]
            provider.create_instances(s['instances'], wait=False)

            p = mp.Process(target=provider.wait_for_running_instances)
            p.start()
            processes += [p]

        for p in processes:
            p.join()

    def stop(self):
        processes = []
        mp = get_context('fork')

        for provider in self._providers.values():
            provider.remove_instances(wait=False)

            p = mp.Process(target=provider.wait_for_removed_instances)
            p.start()
            processes += [p]

        for p in processes:
            p.join()

    def run(self):
        processes = []
        mp = get_context('fork')

        for s in self._session:
            provider = self._providers[s['provider']]
            process = mp.Process(target=provider.run_multiple_workers,
                                 args=(s['concurrency'],
                                       s['repeat'],
                                       self._requests))
            processes += [process]

        for p in processes:
            p.start()

        for p in processes:
            p.join()
