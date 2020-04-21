Technical overview
==================

Storage management
------------------

In a cluster environment, it is common for each user to have a "home folder", usually mounted over NFS. Karvdash tries to apply this notion in a containerized environment: All cluster nodes share a common NFS folder, but this folder is also mounted inside containers as well. Thus, when running a notebook server (like Zeppelin or Jupyter), user data is available in the containerized environment at a well-known path - as it would be in a bare-metal cluster node. This, in addition to the web-based file browser provided by Karvdash, facilitates easy data management for applications, both for providing inputs and collecting outputs.

In Karvdash, there are three such folders/data domains:

* Local: User data that is stored on the cluster nodes themselves via a distributed filesystem. Mounted in containers under ``/local``.
* Remote: User data that is stored on a separate storage device and shared via a network link. Mounted in containers under ``/remote``.
* Shared: Data that is shared among all users (usually stored on the same device providing "remote" storage). Mounted in containers under ``/shared``.

For the first two domains ("local" and "remote") Karvdash creates a subfolder for each user, named after the corresponding username and only allows access within that subfolder (like a "home folder"). This is hidden to the user, meaning that ``/local`` and ``/remote`` are the user subfolders themselves. Users cannot go up a level and check other users' names and files.

.. figure:: images/service-layout.png

   The dashboard runs as a service in Kubernetes and coordinates the execution of other services in particular namespaces. All provisioned containers share common mountpoints that correspond to specific paths in the hosts.

To attach these data folders to service and application containers, Karvdash provides a Kubernetes mutating admission webhook which intercepts all calls to create pods or deployments and injects the appropriate "HostPaths" to respective configurations before they are applied. The Karvdash service itself also has the same data folders mounted in order to present their contents via the dashboard.

Service templates
-----------------

Karvdash provides a way for users to easily configure and start services, by integrating a simple service templating mechanism - practically YAML files with variables. The user can specify execution parameters through the dashboard before deployment, and Karvdash will set other "internal" platform configuration values, such as private Docker registry location, external DNS name, etc. Moreover, Karvdash automatically manages service names when starting multiple services from the same template, while it also allows "singleton" services that can only be deployed once per user.

User namespaces
---------------

Internally, at the Kubernetes level, each Karvdash user is matched to a unique namespace, which also hosts all of the user's services. Containers launched within the namespace are given Kubernetes service accounts which are only allowed to operate within their own namespace. This practice organizes resources per user and isolates users from each other.

For user "test", Karvdash creates the namespace ``karvdash-test`` and binds the ``default`` user account in that namespace to the ``cluster-admin`` cluster role (only for the ``karvdash-test`` namespace).

Service exposure
----------------

To expose services to the user, Karvdash makes use of a Kubernetes ingress - a proxy server. Service templates that provide a user-facing service include an ingress directive. Karvdash effectively:

* Exposes all services on subdomains of the main dashboard domain. These domains are composed of the service name and the username, so they can always be the same, allowing the user to bookmark the location.
* Protects all services with a basic HTTP authentication mechanism, using the dashboard usernames and passwords, where each service can only be accessed by its owner. This helps avoiding any external party visiting a user's service frontend without appropriate credentials.
* Incorporates all services under a common SSL environment, so all data sent back-and-forth through the ingress is encrypted.

Assuming that the dashboard is accessible at ``example.com``, user's "test" Zeppelin service named ``zeppelin`` will be exposed at ``zeppelin-test.example.com``. Karvdash will also inject user's "test" credientials to the service's ingress configuration, so that no other user can access ``zeppelin-test.example.com``. As the ingress will be configured with an SSL certificate for both ``example.com`` and ``*.example.com``, all connections will be SSL terminated.

Registry gateway
----------------

Additionally, Karvdash provides a graphical frontend to a private Docker registry, so users can easily manage available private container images and upload new ones from files (exported images). Note that the registry is shared between users, so each user may add new images, but only admins can delete them.
