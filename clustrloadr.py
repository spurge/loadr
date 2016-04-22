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
    """A Session is a set of multiple providers and merges their output into
    the same output Queue.

    The Session workflow are as follows:
        1. s = Session(Queue)
        2. s.providers({"provider-name": {"type": "<provider-type",
                                         ... provider-config }})
        3. s.start({"provider": "<provider-name>",
                    "instances": <number-of-instances>,
                    "concurrency": <number-of-simultaneous-requests>,
                    "repeat": <request-repeatness>})
        4. s.requests({ request-config })
        5. s.run()
        6. s.stop()
    """

    def __init__(self, output):
        # Added providers as a dict, indexed by name
        self._providers = {}
        # Requests configuration
        self._requests = []
        # Session configuration
        self._session = []
        # Output Queue
        self.output = output

    def add_provider(self, name, provider_type, **config):
        """Adds a provider by name, type and configuration.
        Storea provider indexed by name.
        """

        self._providers[name] = get_provider(provider_type,
                                             self.output,
                                             **config)

    def providers(self, providers={}):
        """Adds multiple providers by a dict, indexed by provider names.
        Loops through the list and adds them with add_provider.
        """

        for name, config in providers.items():
            provider_type = config['type']
            self.add_provider(name,
                              provider_type,
                              **{key: val
                                 for key, val
                                 in config.items()
                                 if key != 'type'})
                              # Remove type property - which whould mess up provider.

        return self._providers

    def requests(self, requests=None):
        """Set requests config and return it.
        If requests config not set, then just return it.
        """

        if requests is not None:
            self._requests = requests

        return self._requests

    def start(self, config=[]):
        """Starts all providers' instances simultaneously and blocks until
        all instances are running.

        Config argument is the session configuration which defines which
        provider to run and with how many instances etc:
            {
                "provider": "<provider-name>",
                "instances": <number-of-instances>,
                "concurrency" <number-of-simultaneous-request-workers>,
                "repeat": <number-of-repeatness>
            }
        """

        self._session = config
        processes = []
        mp = get_context('fork')

        for s in self._session:
            provider = self._providers[s['provider']]
            # Start instance in background and do the waiting later...
            provider.create_instances(s['instances'], wait=False)

            # Then start the waiting in it's on thread which we'll join when
            # all instances has been created.
            p = mp.Process(target=provider.wait_for_running_instances)
            p.start()
            processes += [p]

        # Now wait for all instance waiters to be finished
        for p in processes:
            p.join()

    def stop(self):
        """Stops all providers' instances simultaneously and blocks until
        all instances are stopped.
        """

        processes = []
        mp = get_context('fork')

        for provider in self._providers.values():
            # Stop provider, but we'll do the waiting later on...
            provider.remove_instances(wait=False)

            # Start waiting in it's own thread for later joining.
            p = mp.Process(target=provider.wait_for_removed_instances)
            p.start()
            processes += [p]

        # Now wait for all the waiters to get done.
        for p in processes:
            p.join()

    def run(self):
        """Starts all the workers within all running instances.
        It uses the configuration defined in the start method.
        See documentation for start method.
        """

        processes = []
        mp = get_context('fork')

        for s in self._session:
            provider = self._providers[s['provider']]
            # Start the worker runner in it's own thread for later joining...
            process = mp.Process(target=provider.run_multiple_workers,
                                 args=(s['concurrency'],
                                       s['repeat'],
                                       self._requests))
            processes += [process]

        # Start all of them...
        for p in processes:
            p.start()

        # Now wait for doneness
        for p in processes:
            p.join()
