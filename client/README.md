# Karvdash API Client and CLI

[Karvdash](https://github.com/CARV-ICS-FORTH/karvdash) (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for users, allowing them to launch notebooks and other services, design workflows, and specify parameters related to execution through a user-friendly interface. Karvdash manages users, wires up relevant storage to the appropriate paths inside running containers, securely provisions multiple services under one externally-accessible HTTPS endpoint, while keeping them isolated in per-user namespaces at the Kubernetes level, and provides an identity service for OAuth 2.0/OIDC-compatible applications.

Check out the [user guide and API documentation](https://carv-ics-forth.github.io/karvdash/).

The API client library provides a class to interact with a Karvdash installation using function calls. It also includes a command line tool, `karvdash-client`, to run respective API commands from the CLI.

To use the client library you should provide the API endpoint and an authentication token in a configuration file (an example is shown in the [Python library documentation](https://carv-ics-forth.github.io/karvdash/docs/api.html)). For services running within Karvdash-managed namespaces, this file is automatically created and mounted in pods at `/var/lib/karvdash/config.ini`.
