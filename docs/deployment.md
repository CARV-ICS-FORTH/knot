# Deployment

To deploy Knot you need a typical Kubernetes installation - one that includes a storage controller for handling requests (claims) for persistent volumes and a network controller that assigns IP addresses to "LoadBalancer" type services.

You also need [Helm](https://helm.sh), the [Helm diff plugin](https://github.com/databus23/helm-diff), and [Helmfile](https://github.com/roboll/helmfile) installed.

Apply the the latest Knot `helmfile.yaml` with:
```bash
export KNOT_HOST=example.com
helmfile -f git::https://github.com/CARV-ICS-FORTH/knot.git@helmfile.yaml sync
```

You can apply a specific version by adding the `ref` option at the end of the URL. As an example:
```bash
helmfile -f git::https://github.com/CARV-ICS-FORTH/knot.git@helmfile.yaml?ref=v4.0.0 sync
```

## SSL certificate

By default, the installation issues a self-signed, wildcard certificate for the given `KNOT_HOST`. You need to make sure that at the DNS level, both the domain name and its wildcard point to your server (i.e., both `example.com` and `*.example.com`). If you already know your external IP address, you can use a [nip.io](http://nip.io) name (i.e., set `KNOT_HOST` to `<your IP address>.nip.io`).

If you already have a certificate, place it in a secret in the `ingress-nginx` namespace with:
```bash
kubectl create namespace ingress-nginx
kubectl create secret tls -n ingress-nginx ssl-certificate --key <key file> --cert <crt file>
```

And then skip the self-signing process at installation by specifying `--state-values-set ingress.createSelfsignedCertificate="false"` to helmfile.

## Storage

For storage, Knot uses two persistent volume claims: one for internal state (shared by all services) and one for user files.

To setup Knot on top of existing PVCs, use `--state-values-set storage.stateVolume.existingClaim=<claim name>` and `--state-values-set storage.filesVolume.existingClaim=<claim name>` at the helmfile command line.

Another option is to directly use local storage via `--state-values-set storage.stateVolume.hostPath=<state path>` and `--state-values-set storage.filesVolume.hostPath=<files path>` at the helmfile command line. This is useful for development, single-server setups, or compute clusters, where shared mountpoints are already setup among nodes. Note that direct access to storage may require setting up the appropriate permissions. The respective commands can be found in the Knot's `Makefile`.

## Bare metal setup

The following [script](install-ubuntu.sh) installs Kubernetes and then Knot on a fresh Ubuntu 20.04 machine. It has been tested on a [VirtualBox](https://www.virtualbox.org) machine with 2 CPUs, 4 GB RAM, and a bridged network adapter, as well as a similarly specced VM in the Cloud.
```bash
{% include "install-ubuntu.sh" %}
```
