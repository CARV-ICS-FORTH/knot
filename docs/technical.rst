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

Karvdash provides a way for users to easily configure and start services, by integrating a simple service templating mechanism - practically YAML files with variables. The user can specify execution parameters through the dashboard before deployment, and Karvdash will set other "internal" platform configuration values, such as private container registry location, external DNS name, etc. Moreover, Karvdash automatically manages service names when starting multiple services from the same template, while it also allows "singleton" services that can only be deployed once per user.

To convert a YAML deployment into a Karvdash service template:

* Replace strings with variables where necessary.
* Add a "Template" section with variable names, their default values and optional help text.
* Make sure there is exactly one "Service" section named using the variable ``NAME``. If the template contains multiple services, Karvdash will use the first one (you can skip previous services by labeling them with ``karvdash-hidden=true``).
* Optionally have an "Ingress" section pointing to the service (the dashboard will provide a link to the hostname assigned to the ingress if there is one).

The "Template" section should contain the following fields:

===============  ========  =============================================================================
Field            Required  Description
---------------  --------  -----------------------------------------------------------------------------
``kind``         Yes       Set to ``Template``
``name``         Yes       The template name to show in the dashboard
``description``  No        A simple, short description
``singleton``    No        If set, only one instance of the template can be running (unset by default)
``auth``         No        If set, HTTP authentication should be added by the ingress (set by default)
``datasets``     No        If set, dataset volumes will be mounted in pods (set by default)
``variables``    Yes       The template variables (``name`` and ``default`` required, ``help`` optional)
===============  ========  =============================================================================

An example template is::

    # hello-kubernetes.template.yaml

    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: $NAME
    spec:
      rules:
      - host: $HOSTNAME
        http:
          paths:
          - backend:
              serviceName: $NAME
              servicePort: 8080
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: $NAME
    spec:
      type: ClusterIP
      ports:
      - port: 8080
      selector:
        app: $NAME
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: $NAME
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: $NAME
      template:
        metadata:
          labels:
            app: $NAME
        spec:
          containers:
          - name: $NAME
            image: paulbouwer/hello-kubernetes:1.5
            ports:
            - containerPort: 8080
            env:
            - name: MESSAGE
              value: $MESSAGE
    ---
    kind: Template
    name: Hello Kubernetes
    description: Show a message in a web page
    variables:
    - name: NAME
      default: hello-kubernetes
    - name: HOSTNAME
      default: hello-kubernetes.example.com
    - name: MESSAGE
      default: I just deployed this on Kubernetes!
      help: Message to display

The following variables are automatically set by Karvdash. If they are used in a template, they are not presented to the user, but rather their values are filled in by Karvdash before starting a service.

==================  ==============================================================
Field               Description
------------------  --------------------------------------------------------------
``NAMESPACE``       The namespace that the service will run in
``HOSTNAME``        The external hostname that will be assigned to the service
``REGISTRY``        The private container registry configured for the installation
``PRIVATE_DIR``     The path to the "private" data domain
``PRIVATE_VOLUME``  The volume used for the "private" data domain
``SHARED_DIR``      The path to the "shared" data domain
``SHARED_VOLUME``   The volume used for the "shared" data domain
==================  ==============================================================

Karvdash distinguishes between internal system templates, which are stored in the filesystem and can not be changed, and custom user templates, which are stored as CRDs in Kubernetes in the user's namespace. To manage service templates with ``kubectl`` use the ``templates`` resource identifier (i.e., ``kubectl get templates``).

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

Karvdash implements an OAuth 2.0/OpenID Connect provider, which allows third-party services to request verification of users' identities via standard protocols. Note that OAuth 2.0/OpenID provides only authentication information and it is up to the connecting service to define what users are authorized to do, based on their identities (i.e., username, email, etc.). In addition to the integration with Vouch Proxy for authenticating users to services started by the dashboard, Karvdash also acts as an identity provider to `JupyterHub <https://jupyter.org/hub>`_ and `Argo Workflows <https://argoproj.github.io/workflows>`_. Moreover, Karvdash configures appropriate authorization directives in Argo Workflows, so each user will be allowed to access resources in the corresponding Karvdash-defined namespace.
