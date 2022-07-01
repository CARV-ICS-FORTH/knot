<p align="center">
  <img src="https://github.com/CARV-ICS-FORTH/karvdash/raw/master/docs/images/karvdash-blue.png" alt="Karvdash logo" width="320">
</p>

Karvdash (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for users, allowing them to launch notebooks and other services, design workflows, and specify parameters related to execution through a user-friendly interface. Karvdash manages users, wires up relevant storage to the appropriate paths inside running containers, securely provisions multiple services under one externally-accessible HTTPS endpoint, while keeping them isolated in per-user namespaces at the Kubernetes level, and provides an identity service for OAuth 2.0/OIDC-compatible applications.

Check out the [documentation](https://carv-ics-forth.github.io/karvdash/) (also available in Karvdash under "Documentation" at the user menu). Karvdash is written in [Python](https://www.python.org) using [Django](https://www.djangoproject.com).

![Karvdash services screen](https://github.com/CARV-ICS-FORTH/karvdash/raw/master/docs/images/services-screen.png)

## Deployment

> :warning: **Want to quickly try Karvdash out in the Cloud?** Use the [Kubernetes 1-Click App in the DigitalOcean Marketplace](https://marketplace.digitalocean.com/apps/karvdash?refcode=880f14eedb3a).

Karvdash is deployed using [Helm](https://helm.sh). We develop, test, and run Karvdash on Kubernetes 1.22.x.

To install, you need a running Kubernetes environment with the following features:
* The [cert-manager](https://cert-manager.io) certificate management controller for Kubernetes. This is used for creating certificates automatically for the admission webhooks.
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [nip.io](http://nip.io) if you don't have a DNS entry.
* For storage of Karvdash state, an existing persistent volume claim, or a directory in a shared filesystem mounted at the same path across all Kubernetes nodes.
* For files, either a shared filesystem like the one used for storing the configuration, or an NFS server. If using an NFS server, you should also install the [NFS CSI Driver](https://github.com/kubernetes-csi/csi-driver-nfs).

Karvdash runs side-by-side with [JupyterHub](https://jupyter.org/hub), [Argo Workflows](https://argoproj.github.io/workflows), [Harbor](https://goharbor.io), [Grafana](https://grafana.com)/[Prometheus](https://prometheus.io), and [OpenBio](https://github.com/kantale/OpenBio.eu) providing SSO services to users. For Argo Workflows, Karvdash also configures appropriate authorization directives, so each user will be allowed to access resources in the corresponding Karvdash-defined namespace. For Harbor, Karvdash sets up OAuth authentication, fetches users' CLI secrets, and configures Kubernetes to use them. Harbor is also used to store service templates as Helm charts. When running within the Karvdash-based software stack, OpenBio transparently submits workflows for execution through Argo Workflows, while utilizing the automatically mounted storage to exchange data between steps.

Optionally, you can also have Karvdash act as a frontend to [Datashim](https://github.com/datashim-io/datashim), in which case Karvdash can be used to configure datasets (references to objects in S3 buckets that will be mounted in user containers as files).

Our [Makefile](https://github.com/CARV-ICS-FORTH/karvdash/blob/master/Makefile) deploys all the above for [local development](#Development), using [this](https://github.com/CARV-ICS-FORTH/karvdash/blob/master/helmfile.yaml) configuration for [Helmfile](https://github.com/roboll/helmfile).

Consult the Karvdash [Helm chart README](https://github.com/CARV-ICS-FORTH/karvdash/blob/master/chart/karvdash/README.md) for all deployment options.

## Development

To develop Karvdash in a local Kubernetes environment, like the one provided by [Docker Desktop](https://www.docker.com/products/docker-desktop) for macOS (tested with [versions >= 4.3.x](https://docs.docker.com/docker-for-mac/release-notes/) which use Kubernetes 1.22.4), first prepare the environment with:
```bash
make deploy-requirements
make prepare-develop # Run once
DEVELOPMENT=yes make deploy-local
```

This will setup all requirements (cert-manager and an SSL-enabled ingress controller), as well as optional integrations (JupyterHub, Argo Workflows, Harbor, Grafana/Prometheus, OpenBio), and set up a virtual environment to run Karvdash from the command line. You need to have [Helm](https://helm.sh), the [Helm diff plugin](https://github.com/databus23/helm-diff), and [Helmfile](https://github.com/roboll/helmfile) installed. A proxy will forward all requests locally, including requests to the mutating admission webhook to attach file domains and datasets to service containers, or configure registry credentials.

Then, start the local server and async task worker with:
```bash
make develop
```

When done, point your browser to `https://<your IP address>.nip.io` and login as "admin".

For development on bare metal, check out [these](https://carv-ics-forth.github.io/karvdash/install-bare-metal/) instructions that show how to install *everything*, including Docker and Kubernetes.

## Building images

Container images for Karvdash are [available](https://hub.docker.com/r/carvicsforth/karvdash). To build your own locally, run:
```bash
make container
```

To change the version, edit `VERSION`. The image uses `kubectl` 1.22.4 by default, but this can be changed by setting the `KUBECTL_VERSION` variable before running `make`. You can also set your Docker Hub account or container registry endpoint in `REGISTRY_NAME`.

To test the container in a local Kubernetes environment, run the following and then point your browser to `https://<your IP address>.nip.io`:
```bash
make deploy-requirements
make deploy-local
```

To build and push container images, run:
```bash
make container-push
```

We use `buildx` to build the Karvdash container for multiple architectures (`linux/amd64` and `linux/arm64`).

## Acknowledgements

This project has received funding from European Union’s Horizon 2020 Research and Innovation Programme under Grant Agreement No 825061 (EVOLVE - [website](https://www.evolve-h2020.eu), [CORDIS](https://cordis.europa.eu/project/id/825061)).

The Karvdash logo has been designed by [LOBA](https://www.loba.com).
