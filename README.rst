Artemis parts management system.

Install
=======

1. Install pre-requisites::
   
   * Python and pip
   * Git
   * Java
   * Elasticsearch (1.4.4 series)
   * (see http://www.elasticsearch.org)
   * Elasticsearch mapper pluging (https://github.com/elasticsearch/elasticsearch-mapper-attachments)

2. Get the source::

    git clone https://github.com/cottagelabs/artemis

3. Install the app::

    cd artemis
    pip install -e .

4. Make sure lastintid can be created/written::

    # either check that the privileges for the user that will run the artemis 
    # software allow it to create files in the artemis directory, or create 
    # the following file and change its owner to the same user that will 
    # run the artemis software
    
    touch lastintid
    cat '0' > lastintid
    chown USER:USER lastintid

5. Run the webserver::

    python portality/app.py


Install example
===============

Install commands on a clean installation of Ubuntu_11.10::

    sudo apt-get install python-pip python-dev build-essential 
    sudo pip install --upgrade pip 
    sudo pip install --upgrade virtualenv 
    sudo apt-get install git

    wget https://github.com/downloads/elasticsearch/elasticsearch/elasticsearch-1.4.4.tar.gz
    tar -xzvf elasticsearch-1.4.4.tar.gz
    ./elasticsearch-1.4.4/bin/plugin -install elasticsearch/elasticsearch-mapper-attachments/2.4.3
    ./elasticsearch-1.4.4/bin/elasticsearch start

    git clone http://github.com/cottagelabs/artemis
    cd artemis
    pip install -e .
    
    python portality/app.py
    
You will now find your service running at localhost:5004.


Running as a service
====================

In order to run as a long-lived service, you will need to ensure that elasticsearch
starts when the machine starts up, and also that the Artemis service starts 
when the machine starts up.

Elasticsearch can be auto-started by using the service plugin. This is explained on 
the elasticsearch site.

Once elasticsearch is up and running as a service, you need to ensure that the 
artemis service will come up after machine restart. There are various ways to do this, 
for example supervisord is easy to install and configure on a linux machine.


Backups
=======

All the data used by the Artemis service lives in the elasticsearch index. To 
back up all the data, all you need to do is copy the elasticsearch data folder
(which is in the main elasticsearch folder) to your preferred backup location.
