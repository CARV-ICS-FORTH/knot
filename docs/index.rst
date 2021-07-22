.. figure:: images/karvdash-black.png
   :scale: 20%
   :align: center

Overview
========

Karvdash (Kubernetes CARV dashboard) is a service for facilitating data science in Kubernetes-based environments, by supplying the landing page for users, allowing them to launch notebooks and other services, design workflows, and specify parameters related to execution through a user-friendly interface. Karvdash aims to make it straightforward for domain experts to interact with resources in the underlying infrastructure without having to understand lower-level tools and mechanisms.

In summary, Karvdash provides a web-based, graphical frontend - a `dashboard` - for users to:

* Launch services or applications from customizable templates.
* Organize container images stored in a private Docker registry.
* Manage files that are automatically attached to service and application containers when launched.

Under the hood, Karvdash:

* Securely provisions multiple services under one externally-accessible HTTPS endpoint.
* Performs high-level user management and isolates respective services in per-user Kubernetes namespaces.
* Provides an identity service for authenticating users in OIDC-compatible applications.

Kubernetes provides all the tools to do data sharing, create namespaces, etc., but the exact implementation and structure of the overall environment is left to the developer. Karvdash implements a "traditional" user scheme, which is then mapped to Kubernetes namespaces and service accounts. Kubernetes does not have "users" and no place to "login into" by default. In addition, Karvdash wires up relevant storage to the appropriate paths inside running containers, which significantly simplifies data management. Private and shared files are automatically accessible in all execution contexts and also available through the dashboard.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user
   technical
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
