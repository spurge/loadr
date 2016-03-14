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

from multiprocessing import get_context

import ui

from clustrloadr import Session


class Loadr:

    def __init__(self):
        mp = get_context('fork')

        self._ui = None
        self._ui_process = None
        self._ui_output = mp.Queue()

        self._session = Session(self._session_output)
        self._session_process = None
        self._session_output = mp.Queue()

    def ui(self, name=None, module=None):
        if name is not None:
            self._ui = ui.get_ui(name,
                                 input=self._session_output,
                                 output=self._ui_output)
        elif module is not None:
            self._ui = module(input=self._session_output,
                              output=self._output)

        if self._ui is not None:
            mp = get_context('fork')
            self._ui_process = mp.Process(target=self._ui.start)

    def requests(self, config):
        self._session.requests(config)

    def providers(self, config):
        self._session.providers(config)

    def start(self, config):
        mp = get_context('fork')
        self._process_session = mp.Process(target=self._session.start,
                                           args=(config,))
