loadr
=====

A work in progress.

The aim is to create a simple but powerfull super-load-tester with support for
complex series of requests and true concurrency from several instances.

TODO
----

* Add more providers
	- Glesys
	- Rackspace
	- ...
* I might make providers able to create instance nests.

Install
-------

Run `pip install --editable .` in the loadr directory.

Configure
---------

You need three json files.

### Environments

Defines the environments to run you instances in. There are just two providers
at the moment: **Awsec2** and **Localhost**.


	{
		"awsec2": {
			"type": "Awsec2",
			"profile": "loadr",
			"instance_type": "t2.micro",
			"image_id": "ami-d22932be",
			"region": "eu-central-1"
		}
	}

### Requests

Defines the requests cycle to run from your instances.

	[
		{
			"name": "session",
			"method": "POST",
			"url": "http://host/create-session",
			"body": {
				"key": "sdlkfj"
			},
			"expect": {
				"status": 200
			}
		},
		{
			"method": "POST",
			"url": "http://host/create-stuff",
			"headers": {
				"Authorization": "Bearer {{from('session').json.token}}"
			},
			"body": {
				"some-key": "with data"
			}
		},
		{
			"method": "GET",
			"url": "http://host/stuff/{{from(1).json.stuff_id}}/status",
			"headers": {
				"Authorization": "Bearer {{from(0).json.token}}"
			}
		}
	]

### Session

Defines how much your instances will hit the target(s).

	[
		{
			"environment": "awsec2",
			"instances": 10,
			"concurrency": 100,
			"repeat": 10000
		}
	]


Using it
--------

### loadr

Start loadr with a session, environment and requsts within a ui.

There will be three uis:

* **csv** - which simply prints all data as csv
* **json** - dumps json batches
* **text** - some simple informative text version with statistics

`loadr -s session.json -e environments.json -q requests.json -u Csv`

	Usage: loadr [OPTIONS]

	Options:
	  -s, --session FILENAME       Session configuration json file
	  -e, --environments FILENAME  Environments configuration json file
	  -q, --requests FILENAME      Requests cycle configuration json file
	  -u, --ui TEXT                Which ui to use
	  --help                       Show this message and exit.

### clustrloadr

Runs loadr without the session file. And spits out the data as csv. For quick and easy provider setup testing.

`clustrloadr -p awsec2 -i 10 -c 100 -r 10000 -e environments.json -q requests.json`

	Usage: clustrloadr [OPTIONS]

	Options:
	  -p, --provider TEXT          Which provider to use from the environment
								   config json file
	  -i, --instances INTEGER      Number of instances to run at the provider
	  -c, --concurrency INTEGER    How many concurrent requests per instance
	  -r, --repeat INTEGER         How many times to repeat the whole requests
								   cycle
	  -e, --environments FILENAME  Environments configuration json file
	  -q, --requests FILENAME      Requests cycle configuration json file
	  --help                       Show this message and exit.

### wrkloadr

This is what's running on the instances - and a great way to test the request cycle configuration.

`wrkloadr -c 1 -r requests.json`

	Usage: wrkloadr [OPTIONS] [REQUESTFILE]

	Options:
	  -c, --concurrency INTEGER  How many concurrent requests to send
	  -r, --repeat INTEGER       How many times to repeat the whole requests
								 cycle
	  --help                     Show this message and exit.
