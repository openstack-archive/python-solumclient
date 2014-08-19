Arbor application setup instructions
-------------------------------------

Requirements
 python 2.7+
 
Quick start
--------------

1 Install arborlabs client
    - git clone https://github.com/rackerlabs/arborlabs_client
    - cd arborlabs_client
    - sudo python setup.py install

2 Load authentication information
  - We will create an account for you in Keystone, and provide all the auth info in a file. Assuming that you have stored
    this auth info in a file named openrc, you can setup your environment like so:
    
    - source openrc

3 Setup arborlab client for your repository and run tests
    - arbor-app-setup --application-name=<app_name> --github-url=<githuburl> --test-cmd=<test cmd> [--private]
    
    If the repository is private then pass in the '--private' optional argument.

Arbor-app-setup will ask for your username/password for accessing your github repo.
The username/password will be used for creating a github webhook for your repo to trigger events on git push and pull request,
and for creating a token for Arbor to send back build statuses, (build success/failure) to github.
Running arbor-app-setup will run tests for the very first time. You can check the test results by visiting the hosted logs.

Note:

- The <test cmd> is a file that contains the testing instructions. It is the responsibility of the consumer of the Arbor labs to create this file and make it available within the git repository.

- The 'arbor-app-setup' needs to be run once per repository.




Testing flow steps
-------------------

- Create a pull request from a branch to the master
   - This will trigger tests; check the results on Kabana
- Update the pull request
   - This will re-trigger tests; check the results in Kabana
- Merge the pull request
   - This will re-trigger tests; check the results in Kabana


Support
--------

For any questions, please email arborlabssupport@lists.rackspace.com


