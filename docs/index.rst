.. Evolve integration documentation master file, created by
   sphinx-quickstart on Wed Dec  4 16:05:31 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Karvdash documentation
======================

Karvdash (Kubernetes CARV dashboard) is a service management software for Kubernetes, which runs in Kubernetes as a service itself.

Karvdash provides:

* A web-based graphical frontend - a `dashboard` to:

  * Manage services or applications that run in Kubernetes.
  * Manage container images stored in a private Docker registry.
  * Manage collections of private or shared data that are automatically attached to service and application containers when launched.

* A method to launch services or applications from templates that support setting variables before launch.
* An easy an automated way to isolate services in different Kubernetes namespaces depending on the Karvdash user they belong to.
* An integrated solution to securely provision multiple services under one network address and port.

Kubernetes provides all the tools to do data sharing, create namespaces, etc., but the exact implementation and structure of the overall environment is left to the developer. By making respective choices and following a particular workflow, Karvdash practically imposes a Kubernetes usage methodology, which by design has been tailored to a specific environment (HPC cluster) and type of users (data scientists).

Karvdash also implements a "traditional" user scheme (and all associated mechanisms) which is then mapped to Kubernetes namespaces and service accounts. Kubernetes does not have "users" and no place to "login into", as expected by most high-level platform users.

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
