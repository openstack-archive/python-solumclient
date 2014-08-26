Arbor application setup instructions
-------------------------------------

Requirements
 python 2.7+
 
Quick start
--------------

1 Install arborlabs client

```
$ git clone https://github.com/rackerlabs/arborlabs_client
$ cd arborlabs_client
$ virtualenv .arborclient
$ . .arborclient/bin/activate
$ python setup.py install
``` 

2 Load authentication information

  - We will create an account for you in Keystone, and provide all the auth info in a file. Assuming that you have stored
    this auth info in a file named `arborlabs.openrc`, you can setup your environment like so:
    
```
export OS_USERNAME=<username>
export OS_PASSWORD=<password>
export OS_TENANT_NAME=<tenant>
export OS_AUTH_URL=https://keystone.labs.rs-paas.com/v2.0
export OS_REGION_NAME=RegionOne
```
   
    
```
$ source arborlabs.openrc
```
    
    This will set up environment variables OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL, and OS_REGION_NAME.

3 Setup arborlab client for your repository and run tests

```
$ arbor-app-setup <app_name> --git-uri=<githuburi> --test-cmd=<test cmd> [--public]
```

__If the repository is private the 'githuburi' should be in the format of git://git@github.com:<USER>/<REPO>.git__

__If the repository is public then pass in the '--public' optional argument.__

Arbor-app-setup will ask for your username/password for accessing your github repo.
The username/password will be used for creating a github webhook for your repo to trigger events on pull request creation, update, and merge,
and for creating a token for Arbor to send back build statuses, (build success/failure) to github.
Running arbor-app-setup will run tests for the very first time. You can check the test results by visiting the hosted logs.

Note:

- The 'arbor-app-setup' needs to be run once per repository.

- 'test cmd' is a command that Arborlabs will use for running tests on the repo. The command has to be available on the runtime path of Arborlabs unit test executor (a Docker container). If not it should be made available in the user's repository as a shell script. It is the responsibility of the consumer of the Arbor labs to create such a shell script and make it available within the git repository. Arborlabs also supports running tests using Drone. In that case, the value of '--test-cmd' attribute should be set to 'drone' and '.drone.yml' file should be made available in the github repository.


Testing flow steps
-------------------

- Create a pull request from a branch to the master
   - This will trigger tests; check the results on Kibana
- Update the pull request
   - This will re-trigger tests; check the results in Kibana
- Merge the pull request
   - This will re-trigger tests; check the results in Kibana


Support
--------

For any questions, please email arborlabssupport@lists.rackspace.com


