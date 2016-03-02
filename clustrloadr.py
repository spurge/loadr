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

import providers


def instanciator(instances, concurrency, repeat, output,
                 environment, requests):
    """Creates a provider specified in the environment and makes it create
    instances. Then run workers on all instances and write all ouput to
    specified output writer.
    """

    provider = providers.get_provider(environment)

    if provider is not None:
        provider.create_instances(instances)
        provider.run_multiple_workers(concurrency, repeat, requests, output)
        provider.remove_instances()
        provider.shutdown()
    elif 'type' not in environment:
        raise ValueError('Type of provider not defined')
    else:
        raise ValueError('Unknown provider type: "%s"' % environment['type'])


def sessionizer(session, requests, output):
    """Runs multple instanciators defined by session.
    """

    processes = [Process(target=instanciator,
                         args={'requests':requests, 'output':output, **session})
                 for s in session]

    for p in processes:
        p.start()

    for p in processes:
        p.join()
