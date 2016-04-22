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

import ui

from clustrloadr import Session


class Loadr:
    """This is the main wrapper. It contains an UI and a Session which
    communicate through a this object with a Queue and a Pipe.

    The UI has a Pipe which it uses to call this object's commands.
    These commands calls methods in the Session object.

    The Session has a Queue which it adds it's output data into. The UI object
    subscribes on the Session's Queue.

    The UI runs in it's own thread.
    The Session is thread-safe - so we'll have a listener thread that
    listens for commands from the UI and then invokes the Session.
    """

    def __init__(self):
        mp = get_context('fork')

        # UI empty properties
        self._ui = None
        self._ui_process = None
        self._ui_input, self._ui_output = mp.Pipe()

        # Session creation and it's output Queue
        self._session_output = mp.Queue()
        self._session = Session(self._session_output)

        # Listener thread which listens for UI commands
        self._listener_process = mp.Process(target=self._listener)
        self._listener_process.start()

    def _listener(self):
        """Runs in it's own thread. Listens for commands through the UI's
        Pipe and calls the Session accordingly.
        """

        while True:
            # Data comes as three item lont tuple:
            # (TYPE, COMMAND, ARGUMENT)
            data = self._ui_output.recv()

            if data[0] == 'command':
                if data[1] == 'providers':
                    self._session.providers(data[2])
                elif data[1] == 'requests':
                    self._session.requests(data[2])
                elif data[1] == 'start':
                    self._session.start(data[2])
                elif data[1] == 'run':
                    self._session.run()
                elif data[1] == 'stop':
                    self._session.stop()
                elif data[1] == 'quit':
                    self.quit()

    def ui(self, name=None, module=None):
        """Sets the UI by name or module and starts it within it's own thread.
        """

        if name is not None:
            # UI module was passed by name
            self._ui = ui.get_ui(name,
                                 input=self._session_output,
                                 output=self._ui_input)
        elif module is not None:
            # UI module was passed itself
            self._ui = module(input=self._session_output,
                              output=self._output)

        if self._ui is not None:
            # If UI was found - start it within it's thread
            mp = get_context('fork')
            self._ui_process = mp.Process(target=self._ui.start)
            self._ui_process.start()

    def requests(self, config):
        """Define Session's request configuration.
        """

        self._ui_input.send(('command', 'requests', config))

    def providers(self, config):
        """Define Session's providers by config.
        """

        self._ui_input.send(('command', 'providers', config))

    def start(self, config):
        """Start Session - starts all instances.
        """

        self._ui_input.send(('command', 'start', config))

    def stop(self):
        """Stop Session - stops all instances.
        """

        self._ui_input.send(('command', 'stop'))

    def run(self):
        """Run Session - runs all workers at all instances.
        """

        self._ui_input.send(('command', 'run'))

    def quit(self):
        """Send the stop command and quits current processes.
        """

        self.stop()
        sys.exit(0)
