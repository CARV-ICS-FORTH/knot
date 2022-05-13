Technical overview
==================

Storage management
------------------

In a cluster environment, it is common for each user to have a "home folder", usually mounted over NFS, Lustre, Gluster, etc. Karvdash tries to apply this notion in a containerized environment: Given a cluster-wide shared folder, this folder is also mounted inside containers as well. Thus, when running a notebook server (like Jupyter), user data is available in the containerized environment at a well-known path - as it would be in a bare-metal cluster node. This, in addition to the web-based file browser provided by Karvdash, facilitates easy data management for applications, both for providing inputs and collecting outputs.

In Karvdash, there are two such folders/data domains:

* Private: User data that is private to the user. Mounted in containers under ``/private``.
* Shared: Data that is shared among all users. Mounted in containers under ``/shared``.

For the first domain Karvdash creates a subfolder for each user, named after the corresponding username and only allows access within that subfolder (like a "home folder"). This is hidden to the user, meaning that ``/private`` is the user subfolder itself. Users cannot go up a level and check other users' names and files.

.. figure:: images/service-layout.png

   The dashboard runs as a service in Kubernetes and coordinates the execution of other services in particular namespaces. All provisioned containers of a user share common volumes.

To attach these data folders to service and application containers, Karvdash creates Persistent Volumes and associated Persistent Volume Claims for each user, and provides a Kubernetes mutating admission webhook which intercepts all calls to create pods or deployments and injects the appropriate volumes to respective configurations before they are applied. The Karvdash service itself also has the same data folders mounted in order to present their contents via the dashboard. Also, another validating admission webhook makes sure that only allowed host paths can be mounted in pods.

Remote datasets
---------------

In addition to the "private" and "shared" data domains, Karvdash optionally interfaces with `Datashim <https://github.com/datashim-io/datashim>`_ to mount internal or external S3 and H3 buckets to running containers. Karvdash provides the frontend to configure datasets and then attaches the produced Persistent Volume Claims to deployed pods. Datasets are mounted in containers at ``/mnt/datasets/<name>``.

Service templates
-----------------

Karvdash provides a way for users to easily configure and start services, by integrating a service templating mechanism based on `Helm <https://helm.sh>`_. Helm service templates, named "charts", are packaged and placed within an artifact registry, like `Harbor <https://goharbor.io>`_. The list of available services includes global and user-specific charts, which are automatically discovered by Karvdash.

When deploying a service, the user can specify chart values through the dashboard. Karvdash will silently set "internal" platform configuration values, such as the generated hostname assigned to the service, the location of the private container registry, etc.

Karvdash-compatible charts may use the following values:

.. |check| raw:: html

    &check;

===============================  =========================================================================================  ===========
Value                            Description                                                                                Set in env.
-------------------------------  -----------------------------------------------------------------------------------------  -----------
``karvdash.enabled``             Set to ``true``
``karvdash.hostname``            The hostname assigned to the service (set to ``<release name>-<username>.<ingress url>``)
``karvdash.username``            The user's username                                                                        |check|
``karvdash.namespace``           The user's namespace                                                                       |check|
``karvdash.ingressUrl``          The dashboard's URL                                                                        |check|
``karvdash.privateDir``          The path to the "private" data domain                                                      |check|
``karvdash.privateVolume``       The volume used for the "private" data domain                                              |check|
``karvdash.sharedDir``           The path to the "shared" data domain                                                       |check|
``karvdash.sharedVolume``        The volume used for the "shared" data domain                                               |check|
``karvdash.argoWorkflowsUrl``    The URL of the Argo Worfklows service (set if Argo Workflows is enabled)                   |check|
``karvdash.privateRegistryUrl``  The URL of the "private" container registry (set if Harbor is enabled)                     |check|
``karvdash.publicRegistryUrl``   The URL of the "shared" container registry (set if Harbor is enabled)                      |check|
``karvdash.privateRepoUrl``      The URL of the "private" Helm chart repository (set if Harbor is enabled)                  |check|
``karvdash.publicRepoUrl``       The URL of the "shared" Helm chart repository (set if Harbor is enabled)                   |check|
===============================  =========================================================================================  ===========

As shown in the table, some values are also set inside pods as environment variables (in uppercase snake case, i.e. ``KARVDASH_PRIVATE_DIR``).

Karvdash will show all services to the user, except those marked with the label ``karvdash-hidden``. Upon deployment, Karvdash will attach local storage folders to all pods, as well as remote datasets (except on pods labelled with ``karvdash-no-datasets``). Authentication directives are added to all ingress resources (except on those labelled with ``karvdash-no-auth``).

User namespaces
---------------

Internally, at the Kubernetes level, each Karvdash user is matched to a unique namespace, which also hosts all of the user's services. Containers launched within the namespace are given Kubernetes service accounts which are only allowed to operate within their own namespace. This practice organizes resources per user and isolates users from each other.

For user "test", Karvdash creates the namespace ``karvdash-test`` and binds the ``default`` user account in that namespace to the ``cluster-admin`` cluster role (only for the ``karvdash-test`` namespace).

Service exposure
----------------

To expose services to the user, Karvdash makes use of a Kubernetes ingress - a proxy server. Service templates that provide a user-facing service include an ingress directive. Karvdash effectively:

* Exposes all services on subdomains of the main dashboard domain. These domains are composed of the service name and the username, so they can always be the same, allowing the user to bookmark the location.
* Protects all services with an authentication/authorization mechanism, by configuring each respective ingress to perform single sing-on through the dashboard. The default deployment integrates `Vouch Proxy <https://github.com/vouch/vouch-proxy>`_ as an OAuth 2.0/OIDC client to the dashboard, which in turn provides credentials to the NGINX-based web proxy implementing the ingress. Thus, each service can only be accessed by its owner. This helps avoiding any external party visiting a user's service frontend without appropriate credentials.
* Incorporates all services under a common SSL environment, so all data sent back-and-forth through each ingress is encrypted.

Assuming that the dashboard is accessible at ``example.com``, the "File Browser" service named ``browser`` started by user "test" will be exposed at ``browser-test.example.com``. Karvdash will also inject appropriate rules to the service's ingress configuration, so that no other user can access ``browser-test.example.com``. As the ingress will be configured with an SSL certificate for both ``example.com`` and ``*.example.com``, all connections will be SSL terminated.

SSO service
-----------

Karvdash implements an OAuth 2.0/OIDC provider, which allows third-party services to request verification of users' identities via standard protocols. In the OIDC response, Karvdash also sets extra data that may be useful to connected services (all environment variables mentioned in :ref:`Service templates`, but in lowercase, i.e. ``karvdash_private_dir``).

Note that OAuth 2.0/OIDC provides only authentication information and it is up to the connecting service to define what users are authorized to do, based on their identities (i.e., username, email, etc.). In addition to the integration with Vouch Proxy for authenticating users to services started by the dashboard, Karvdash also acts as an identity provider to `JupyterHub <https://jupyter.org/hub>`_, `Argo Workflows <https://argoproj.github.io/workflows>`_, `Harbor <https://goharbor.io>`_, and other services that may be installed side-by-side to the dashboard. For compatible services, Karvdash also configures user authorization to resources. For example, in Argo Workflows, Karvdash sets the appropriate role bindings so that users will only be allowed to access workflows in their respective Karvdash-defined namespaces.
