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

import requests


class Glesys:
    apiurl = 'https://api.glesys.com/%s/%s'
    apimethod = 'POST'

    def __init__(self, config):
        self.config = config

    def gc(self, key):
        if key in config:
            return config[key]

        raise Exception('"%s" was not found in environment' % key)

    def send(self, module, command, data):
        req = Request(self.apimethod,
                      self.apiurl % (module, command),
                      data=data)

    def get_instances(self, count):
        for i in range(count):
            hostname = self.generate_hostname()
            passwd = self.generate_passwd()

            req = self.send('server', 'create',
                            {'apiuser': self.gc('apiuser'),
                             'apikey': self.gc('apikey'),
                             'datacenter': self.gc('datacenter'),
                             'platform': 'openvz',
                             'hostname': hostname,
                             'templatename': self.gc('template'),
                             'disksize': '5gb',
                             'cpucores': self.gc('cpu'),
                             'memorysize': self.gc('memory'),
                             'rootpassword': passwd})
