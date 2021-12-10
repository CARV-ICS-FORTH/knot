<p align="center">
  <img src="https://github.com/CARV-ICS-FORTH/karvdash/raw/master/docs/images/karvdash-blue.png" alt="Karvdash logo" width="320">
</p>

Karvdash (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for users, allowing them to launch notebooks and other services, design workflows, and specify parameters related to execution through a user-friendly interface. Karvdash manages users, wires up relevant storage to the appropriate paths inside running containers, securely provisions multiple services under one externally-accessible HTTPS endpoint, while keeping them isolated in per-user namespaces at the Kubernetes level, and provides an identity service for OAuth 2.0/OIDC-compatible applications.

Check out the [user guide and API documentation](https://carv-ics-forth.github.io/karvdash/) (also available in Karvdash under "Documentation" at the user menu). Karvdash is written in [Python](https://www.python.org) using [Django](https://www.djangoproject.com).

![Karvdash services screen](https://github.com/CARV-ICS-FORTH/karvdash/raw/master/docs/images/services-screen.png)

## Deployment

> :warning: **Want to quickly try Karvdash out in the Cloud?** Use the [Kubernetes 1-Click App in the DigitalOcean Marketplace](https://marketplace.digitalocean.com/apps/karvdash?refcode=880f14eedb3a).

Karvdash is deployed using [Helm](https://helm.sh) (version 3). We use Kubernetes 1.19.x to develop, test, and run Karvdash on both `amd64` and `arm64` architectures.

To install, you need a running Kubernetes environment with the following features:
* The [cert-manager](https://cert-manager.io) certificate management controller for Kubernetes. This is used for creating certificates automatically for the admission webhooks. We use [this](https://artifacthub.io/packages/helm/jetstack/cert-manager) Helm chart.
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [nip.io](http://nip.io) if you don't have a DNS entry. We use [this](https://artifacthub.io/packages/helm/ingress-nginx/ingress-nginx) Helm chart.
* For storage of Karvdash state, an existing persistent volume claim, or a directory in a shared filesystem mounted at the same path across all Kubernetes nodes.
* For files, either a shared filesystem like the one used for storing the configuration, or an NFS server. If using an NFS server, you should also install the [NFS CSI Driver](https://github.com/kubernetes-csi/csi-driver-nfs). We use [these](https://github.com/kubernetes-csi/csi-driver-nfs/tree/master/charts) instructions to install via Helm.

Karvdash can run side-by-side with [JupyterHub](https://jupyter.org/hub) and [Argo Workflows](https://argoproj.github.io/workflows), providing SSO services to users. For Argo Workflows, Karvdash also configures appropriate authorization directives, so each user will be allowed to access resources in the corresponding Karvdash-defined namespace. We use [this](https://zero-to-jupyterhub.readthedocs.io/en/latest/) Helm chart for JupyterHub and [this](https://github.com/argoproj/argo-helm) one for Argo Workflows.

Optionally, you can also have Karvdash act as a frontend to:
* A private container registry. You can run the one from Docker using [these](https://docs.docker.com/registry/deploying/) instructions, or [this](https://artifacthub.io/packages/helm/twuni/docker-registry) Helm chart.
* [Datashim](https://github.com/datashim-io/datashim), in which case Karvdash can be used to configure datasets (references to objects in S3 buckets that will be mounted in user containers as files).

Our [Makefile](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/Makefile) deploys all the above for [local development](#Development).

To deploy Karvdash, first add the repo and then install. For example:

```bash
helm repo add karvdash https://carv-ics-forth.github.io/karvdash/chart
helm install karvdash karvdash/karvdash --namespace default \
    --set karvdash.ingressURL=https://example.com \
    --set karvdash.stateHostPath=/mnt/nfs/karvdash \
    --set karvdash.filesURL=file:///mnt/nfs
```

Some of the variables set above are required. The table below lists all available options:

| Variable                            | Required | Description                                                                                | Default                           |
|-------------------------------------|----------|--------------------------------------------------------------------------------------------|-----------------------------------|
| `image`                             |          | Container image to use.                                                                    | `carvicsforth/karvdash:<version>` |
| `rbac.create`                       |          | Assign full permissions to Karvdash, API and namespace discovery to authenticated users.   | `true`                            |
| `karvdash.stateVolumeClaim`         | &check;  | If set, use this persistent volume claim for storing state.                                |                                   |
| `karvdash.stateHostPath`            | &check;  | The host path to use for storing state, when no existing volume claim is set.              |                                   |
| `karvdash.logsVolumeClaim`          |          | The volume to store HTTP access and error logs.                                            |                                   |
| `karvdash.logsHostPath`             |          | The host path to use for storing logs, when no existing volume claim is set.               |                                   |
| `karvdash.themeVolumeClaim`         |          | If set, use this persistent volume claim for overriding the theme files.                   |                                   |
| `karvdash.themeHostPath`            |          | The host path to use for overriding the theme files, when no existing volume claim is set. |                                   |
| `karvdash.djangoSecret`             |          | Secret for Django. Use a random string of 50 characters.                                   | autogenerated                     |
| `karvdash.djangoDebug`              |          | Set to anything to enable, empty to disable.                                               |                                   |
| `karvdash.timeout`                  |          | Timeout in seconds for gunicorn workers.                                                   | `180`                             |
| `karvdash.adminPassword`            |          | The default admin password.                                                                | `admin`                           |
| `karvdash.ldapServerURL`            |          | The URL of the LDAP server to use for authentication (include DN and password).            |                                   |
| `karvdash.ldapUserDNTemplate`       |          | String template that describes any user’s DN based on the username.                        |                                   |
| `karvdash.ldapUserAttrMap`          |          | A mapping from user field names to LDAP attribute names (in JSON format).                  | `{"username": "cn"}`              |
| `karvdash.htpasswdExportDir`        |          | If set, the path to export the htpasswd file in (only for local users).                    |                                   |
| `karvdash.dashboardTitle`           |          | The title of the dashboard.                                                                | `Karvdash`                        |
| `karvdash.documentationURL`         |          | If set, override the internal "Documentation" URL in the user menu.                        |                                   |
| `karvdash.issuesURL`                |          | If set, an option to "Report an issue" is shown in the user menu.                          |                                   |
| `karvdash.ingressURL`               | &check;  | The ingress URL used.                                                                      |                                   |
| `karvdash.registryURL`              |          | The URL of the container registry.                                                         |                                   |
| `karvdash.registryCert`             |          | The container registry certificate (use if self-signed).                                   |                                   |
| `karvdash.datasetsAvailable`        |          | Set to anything to enable dataset management.                                              |                                   |
| `karvdash.filesURL`                 | &check;  | The base URL for the private and shared file domains.                                      |                                   |
| `karvdash.filesSize`                |          | The size for the files persistent volume.                                                  | `1Pi`                             |
| `karvdash.allowedHostPathDirs`      |          | Other host paths to allow attaching to containers (separate with `:`).                     |                                   |
| `karvdash.disabledServiceTemplates` |          | List of service templates to disable on deployment (filenames).                            |                                   |
| `karvdash.disabledDatasetTemplates` |          | List of dataset templates to disable on deployment (identifiers).                          |                                   |
| `karvdash.serviceURLPrefixes`       |          | List of predefined URL prefixes for services.                                              |                                   |
| `karvdash.jupyterHubURL`            |          | JupyterHub URL for integration with notebook frontend.                                     |                                   |
| `karvdash.jupyterHubNamespace`      |          | JupyterHub namespace for integration.                                                      |                                   |
| `karvdash.jupyterHubNotebookDir`    |          | Directory to create in the private file domain for JupyterHub notebooks.                   |                                   |
| `karvdash.argoWorkflowsURL`         |          | Argo Workflows URL for integration with workflow frontend.                                 |                                   |
| `karvdash.argoWorkflowsNamespace`   |          | Argo Workflows namespace for integration.                                                  |                                   |

Set `karvdash.filesURL` to:
* `file://<path>`, if using a node-wide, shared mountpoint for files.
* `nfs://<server>/<path>`, if using an NFS server for files.

Karvdash will create `private/<username>`, `shared`, and `uploads` folders within.

The state volume is used to store the database, the running services repository, and the template library. You can either use an existing peristent storage claim with `karvdash.stateVolumeClaim`, or set `karvdash.stateHostPath` to automatically create one (this must accessible by all nodes). Create a `templates` directory inside the state volume to add new service templates or override defaults (the ones in [templates](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/templates)). Templates placed there will be available as read-only to all users.

The theme volume is used to replace the default [theme directory](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/dashboard/static/dashboard/theme) and should contain variants of all existing files.

To remove Karvdash, uninstall using `helm uninstall karvdash`, which will remove the service, admission webhooks, and RBAC rules, but not associated CRDs. You can use the YAML files in [crds](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/chart/karvdash/crds) to remove them.

## Development

To develop Karvdash in a local Kubernetes environment, like the one provided by [Docker Desktop](https://www.docker.com/products/docker-desktop) for macOS (tested with [versions >= 2.5.x.x](https://docs.docker.com/docker-for-mac/release-notes/) which uses Kubernetes 1.19.3), run:
```bash
make deploy-requirements
make prepare-develop
./manage.py runserver
```

This will setup all requirements (a private container registry, cert-manager, an SSL-enabled ingress controller, JupyterHub, and Argo Workflows) and set up a virtual environment to run Karvdash from the command line. You need to have [Helm](https://helm.sh) installed (version 3). When done, point your browser to http://127.0.0.1:8000 and login as "admin". Note, however, that when running Karvdash outside Kubernetes, there is no mutating admission webhook to attach file domains and datasets to service containers (use `make deploy-local` after `make deploy-requirements` for running locally in a container).

Also, some versions of Docker Desktop [do not enforce RBAC rules](https://github.com/docker/for-mac/issues/3694), so there is no namespace isolation. Run the following commands to enable namespace isolation and explicitly set permissions for the `default` service account in the `default` namespace (used by Docker Desktop):
```bash
kubectl delete clusterrolebinding docker-for-desktop-binding
kubectl create clusterrolebinding default-cluster-admin --clusterrole=cluster-admin --serviceaccount=default:default
```

## Building images

Container images for Karvdash are [available](https://hub.docker.com/r/carvicsforth/karvdash). To build your own locally, run:
```bash
make container
```

To change the version, edit `VERSION`. The image uses `kubectl` 1.19.8 by default, but this can be changed by setting the `KUBECTL_VERSION` variable before running `make`. You can also set your Docker Hub account or container registry endpoint in `REGISTRY_NAME`.

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

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 825061 (EVOLVE - [website](https://www.evolve-h2020.eu), [CORDIS](https://cordis.europa.eu/project/id/825061)).

The Karvdash logo has been designed by [LOBA](https://www.loba.com).
