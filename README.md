loadr
=====

loadr.py
-------

* Takes arguments:
	- AWS profile
	- Concurrency
	- Number of cycles
	- `wrkloadr` setup/cycle file
* Wraps
	- `ec2-clusterizer` with machines * (concurrency / cpu)
	- `wrkloadr` with setup/cycle file and loaded into `ec2-clusterizer`

ec2-clusterizer
---------------

* Initializes x ec2 machines
* Uploads & runs specified code in some wrapped mode
* Runs one process for each cpu or by other specification
* Takes all `stdout` from each ec2-node process and sends it back home
* Merges all gathered `stdout` to a single stream

wrkloadr
--------

* Parses setup/call-cycle file
* Starts making http(s) requests defined by call-cycle
* Output stats as `csv` to `stdout`
