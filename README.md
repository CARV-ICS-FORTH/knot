<p align="center">
  <img src="https://github.com/CARV-ICS-FORTH/knot/raw/master/docs/images/logo.png" alt="Knot logo" width="320">
</p>

Knot is a complete environment for doing actual work on [Kubernetes](https://kubernetes.io). It includes a complete set of web-based tools to help you unleash your productivity, without ever needing to use the command line. At its core, the Knot dashboard supplies the landing page for users, allowing them to launch notebooks and other services, design workflows, and specify parameters related to execution through a user-friendly interface. The dashboard manages users, wires up relevant storage to the appropriate paths inside running containers, securely provisions multiple services under one externally-accessible HTTPS endpoint, while keeping them isolated in per-user namespaces at the Kubernetes level, and provides an identity service for OAuth 2.0/OIDC-compatible applications.

![Knot services screen](https://github.com/CARV-ICS-FORTH/knot/raw/master/docs/images/services-screen.png)

The Knot installation includes [JupyterHub](https://jupyter.org/hub), [Argo Workflows](https://argoproj.github.io/workflows), [Harbor](https://goharbor.io), and [Grafana](https://grafana.com)/[Prometheus](https://prometheus.io), all accessible through the dashboard. Behind the scenes, other popular tools are automatically installed to help with the integration, such as [cert-manager](https://cert-manager.io), the [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/), [Vouch Proxy](https://github.com/vouch/vouch-proxy), and the [NFS CSI Driver](https://github.com/kubernetes-csi/csi-driver-nfs). Knot also uses [Helm](https://helm.sh) charts internally for implementing service templates.

Check out the [documentation](https://carv-ics-forth.github.io/knot/docs/) (also available in the Knot dashboard under "Documentation" at the user menu), which includes installation instructions, a user guide, and technical notes on how Knot works internally. The Knot dashboard is written in [Python](https://www.python.org) using [Django](https://www.djangoproject.com).

## Deployment

To deploy Knot you need a typical Kubernetes installation, [Helm](https://helm.sh), the [Helm diff plugin](https://github.com/databus23/helm-diff), and [Helmfile](https://github.com/roboll/helmfile) installed. We develop, test, and run Knot on Kubernetes 1.22.x.

Apply the the latest Knot `helmfile.yaml` with:
```bash
export KNOT_HOST=example.com
helmfile -f git::https://github.com/CARV-ICS-FORTH/knot.git@helmfile.yaml sync
```

The variable `KNOT_HOST` is necessary. By default, we use [cert-manager](https://cert-manager.io) to self-sign a wildcard certificate for the given host. You need to make sure that at the DNS level, both the domain name and its wildcard point to your server (i.e., both `example.com` and `*.example.com`). If you already know your external IP address, you can use a [nip.io](http://nip.io) name (i.e., set `KNOT_HOST` to `<your IP address>.nip.io`).

For storage, Knot uses two persistent volume claims: one for internal state (shared by all services) and one for user files. You can use helmfile variables to setup Knot on top of existing PVCs, or skip the storage controller and directly use local storage (useful for single-server, bare metal setups).

Deployment options are discussed in the [deployment chapter](https://carv-ics-forth.github.io/knot/docs/deployment.html) of the [documentation](https://carv-ics-forth.github.io/knot/docs/).

## Development

To develop Knot in a local Kubernetes environment, like the one provided by [Docker Desktop](https://www.docker.com/products/docker-desktop) for macOS (tested with [versions >= 4.3.x, <= 4.7.x](https://docs.docker.com/docker-for-mac/release-notes/) which use Kubernetes 1.22.x), first create and populate the Python virtual environment with:
```bash
make prepare-develop
```

Then install Knot in a special configuration, where all requests to the dashboard are forwarded locally:
```bash
make deploy
```

Then, start the local server and async task worker with:
```bash
make develop
```

When done, point your browser to `https://<your IP address>.nip.io` and login as "admin".

## Building images

Container images for the Knot dashboard are [available](https://hub.docker.com/r/carvicsforth/knot).

To build your own locally, run:
```bash
make container
```

To change the version, edit `VERSION`. Other variables, like the `kubectl` version and the container registry name are set in the `Makefile`.

To test the container in a local Kubernetes environment, run:
```bash
make deploy-test
```

Then point your browser to `https://<your IP address>.nip.io` and login.

To build and push the container image, run:
```bash
make container-push
```

We use `buildx` to build the Knot container for multiple architectures (`linux/amd64` and `linux/arm64`) automatically when a new version tag is pushed. This also triggers publishing the corresponding [Knot dashboard Helm chart](https://github.com/CARV-ICS-FORTH/knot/blob/master/chart/knot/README.md).
