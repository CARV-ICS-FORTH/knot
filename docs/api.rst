API documentation
=================

Karvdash (Kubernetes CARV dashboard) provides a REST API for performing service management from external systems.

The API includes the following methods under the API's base URL (i.e. ``http://karvdash.default.svc/api``):

======  =====================  =============================================
Method  Path                   Description
------  ---------------------  ---------------------------------------------
GET     ``/services/``         List running services
POST    ``/services/``         Create/start a service
POST    ``/services/<name>/``  Execute a command at service pods
DELETE  ``/services/<name>/``  Delete/stop a running service
GET     ``/templates/``        List available templates
======  =====================  =============================================

All methods use a JSON dictionary for input data (if applicable) and respond using JSON formatting. For a detailed description of request and response variables consult the `Python library`_ documentation.

A Python library called ``karvdash_client`` has been implemented to easily use the API in any Python script. The library also comes with a CLI utility, ``karvdashctl`` which allows interfacing with Karvdash through the shell. The client library and CLI utility can be particularly useful for managing services through a Zeppelin notebook.

To use the client library you should provide the API endpoint and an authentication token in a configuration file (an example is shown in the `Python library`_ documentation). For services running with the Karvdash mutating admission webhook activated, this file is automatically created and mounted in pods at ``/var/lib/karvdash/config.ini``.

Command line tool
-----------------

The ``karvdashctl`` tool has a ``--help`` flag to show available commands::

    $ karvdashctl -h
    usage: karvdashctl [-h] [--config CONFIG]
                       {list_services,create_service,exec_service,delete_service,list_templates}
                       ...

    Karvdash API client command line tool

    optional arguments:
      -h, --help            show this help message and exit
      --config CONFIG       Karvdash API client configuration file

    API command:
      {list_services,create_service,exec_service,delete_service,list_templates}
        list_services       List running services
        create_service      Create a service from a template
        exec_service        Execute a command at a running service
        delete_service      Delete a running service
        list_templates      List available templates

And comes with help text for each individual command::

    $ karvdashctl create_service --help
    usage: karvdashctl create_service [-h] filename variables [variables ...]

    positional arguments:
      filename    Template filename
      variables   Template variables as key=value pairs (provide at least a
                  "name")

    optional arguments:
      -h, --help  show this help message and exit

Python library
--------------

.. autoclass:: karvdash_client.api.API
   :members:
   :undoc-members:
   :member-order: bysource
