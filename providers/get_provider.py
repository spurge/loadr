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


def get_provider(name, output, **config):
    """Creates provider by type and initiate it with specified config
    arguments. Raises ValueError if specified provider doesn't exists.
    """

    try:
        exec('from providers.{1} import {0}'
             .format(name, name.lower()))
        provider = locals()[name](**config, output=output)
    except ImportError:
        raise ValueError('No provider with name "{}" in "providers.{}"'
                         .format(name, name.lower()))

    return provider
