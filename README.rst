Artemis parts management system.

Based on parts of BibServer and Edjo and FacetView

Install
=======

1. Install pre-requisites::
   
   * Python and pip
   * Git
   * Java
   * Elasticsearch (> 0.17 series)
   * (see http://www.elasticsearch.org/download/ and http://www.elasticsearch.org/guide/reference/setup/installation.html)
   * Elasticsearch mapper pluging (https://github.com/elasticsearch/elasticsearch-mapper-attachments)

2. Get the source::

    git clone https://github.com/cottagelabs/artemis

3. Install the app::

    cd artemis
    pip install -e .

4. Make sure lastintid and lastintbatch can be created/written::

    # either check that the privileges for the user that will run the artemis 
    # software allow it to create files in the artemis directory, or create 
    # the following files and change their owner to the same user that will 
    # run the artemis software
    
    touch lastintid
    cat '0' > lastintid
    touch lastintbatch
    cat '0' > lastintbatch
    chown USER:USER lastintid
    chown USER:USER lastintbatch

5. Run the webserver::

    python artemis/web.py

6. If you want to pre-load with legacy data::

    python extra/import.py

Install example
===============

Install commands on a clean installation of Ubuntu_11.10::

    sudo apt-get install python-pip python-dev build-essential 
    sudo pip install --upgrade pip 
    sudo pip install --upgrade virtualenv 
    sudo apt-get install git

    wget https://github.com/downloads/elasticsearch/elasticsearch/elasticsearch-0.18.2.tar.gz
    tar -xzvf elasticsearch-0.18.2.tar.gz
    ./elasticsearch-0.18.2/bin/plugin -install elasticsearch/elasticsearch-mapper-attachments/1.0.0
    ./elasticsearch-0.18.2/bin/elasticsearch start

    git clone http://github.com/cottagelabs/artemis
    cd artemis
    pip install -e .
    
    python artemis/web.py
    
You will now find your service running at localhost:5004.


Running as a service
====================

In order to run as a long-lived service, you will need to ensure that elasticsearch
starts when the machine starts up, and also that the Artemis service starts 
when the machine starts up.

Elasticsearch can be auto-started by using the service plugin. This is explained on 
the elasticsearch installation page at::

    http://www.elasticsearch.org/guide/reference/setup/installation.html

The location for the service wrapper code, and install instuctions, are here::

    https://github.com/elasticsearch/elasticsearch-servicewrapper.git

Once elasticsearch is up and running as a service, you need to ensure that the 
artemis service will come up after machine restart. There is no specific way to 
do this, other than on a linux machine creating a startup script and placing it 
in your /etc/init.d/ folder.


Backups
=======

All the data used by the Artemis service lives in the elasticsearch index. To 
back up all the data, all you need to do is copy the elasticsearch data folder
(which is in the main elasticsearch folder) to your preferred backup location.
