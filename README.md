loadr
=====

A work in progress.

The aim is to create a simple but powerfull super-load-tester with support for
complex series of requests and true concurrency from several instances.

TODO
----

* Localhost-provider which also works as a superclass for other providers and
  provder tests.
* Separate fetched data from remote instances in awsec2.
* Rewrite `clustrloadr.py` to first initiate all providers with instances and
  then launch all workers at the same time.
* Write tests for `clustrloadr.py` and `workrloadr.py`.
* UIs: csv, ncurses and json.
* Rewrite `cli.py` with three threads:
	- Main-thread which parses config files and launches the two other threads.
	- UI-thread which has a `Pipe` and a `Queue` connected to the
	  Cluster-thread.
	- Cluster-thread which uses `clustrloadr.py` to launch instances.

loadr.py
--------

* Wraps
	- `clustrloadr.py` with instances/machines
	- `wrkloadr.py` with setup/cycle file and wrapped within `clustrloadr.py`
* Gathers all `csv` and merge it into something readable
	- `ncurses`-based ui
	- `json`-batches for a web ui
	- ...

clustrloadr.py
--------------

* Parses a provided environment config json file
* Initializes instances at some provider
* Uploads & runs specified code in some wrapped mode (`wrkloadr.py`)
* Merges all gathered `stdout` to a single stream

wrkloadr.py
-----------

* Parses setup/call-cycle file
* Starts making http(s) requests defined by call-cycle, concurrency and number of repeats
* Output stats as `csv` to `stdout` or specified file
