# Karvdash

Karvdash (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for working on a Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

Check out the [user guide and API documentation](https://carv-ics-forth.github.io/karvdash/) (also available in Karvdash under "Documentation" at the user menu). Karvdash is written in [Python](https://www.python.org) using [Django](https://www.djangoproject.com).

![Karvdash services screen](https://github.com/CARV-ICS-FORTH/karvdash/raw/master/docs/images/services-screen.png)

## Compatibility

We use Kubernetes 1.19.x to develop, test, and run Karvdash on both `amd64` and `arm64` architectures.

Karvdash includes service templates for [Zeppelin](https://zeppelin.apache.org) 0.9.0, [Jupyter](https://jupyter.org) (Jupyter Core 4.7.0 with Jupyter Notebook 6.1.6, as bundled with [TensorFlow](http://www.tensorflow.org) 2.3.2), [Argo](https://argoproj.github.io) (both [Argo Workflows](https://github.com/argoproj/argo) 2.12.10 and [Argo Events](https://github.com/argoproj/argo-events) 1.2.3), and other applications.

The Zeppelin template uses a Karvdash-specific Docker image which adds `kubectl` 1.19.8, the `argo` utility (at the same version as the Argo service template), `karvdashctl` to manage Karvdash services from a notebook, [Spark](http://spark.apache.org) 2.4.5 with [Hadoop](https://hadoop.apache.org) 2.7, as well as the [evolve](https://bitbucket.org/sunlightio/evolve_python_library/) Python library from [Sunlight.io](https://sunlight.io), that allows building Argo workflows in Python.

The Zeppelin "with GPU support" template uses the above image with [CUDA](https://developer.nvidia.com/cuda-toolkit) 10.1 and TensorFlow 2.3.2 preinstalled, as well as the necessary directives to place the resulting container in a node with a GPU. A corresponding Jupyter "with GPU support" template is also included.

If your application requirements differ, you will need to create custom Docker images and service templates.

> :warning: **`arm64` support is experimental:** Zeppelin and some other services do not currently work on `arm64`.

## Deployment

Karvdash is deployed using [Helm](https://helm.sh) (version 3).

To install, you need a running Kubernetes environment with the following features:
* The [cert-manager](https://cert-manager.io) certificate management controller for Kubernetes. This is used for creating certificates automatically for the admission webhooks. We use [this](https://artifacthub.io/packages/helm/jetstack/cert-manager) Helm chart.
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [nip.io](http://nip.io) if you don't have a DNS entry. We use [this](https://artifacthub.io/packages/helm/ingress-nginx/ingress-nginx) Helm chart.
* For storage of Karvdash state, an existing persistent volume claim, or a directory in a shared filesystem mounted at the same path across all Kubernetes nodes, like NFS, [Gluster](https://www.gluster.org), or similar.
* For files, either a shared filesystem like the one used for storing the configuration, or an NFS server. If using an NFS server, you should also install the [NFS CSI Driver](https://github.com/kubernetes-csi/csi-driver-nfs). We use [these](https://github.com/kubernetes-csi/csi-driver-nfs/tree/master/charts) instructions to install via Helm.

Optionally:
* A private Docker registry. You can run one using the [official instructions](https://docs.docker.com/registry/deploying/), or use [this](https://artifacthub.io/packages/helm/twuni/docker-registry) Helm chart.
* [Datashim](https://github.com/datashim-io/datashim), in which case Karvdash can be used to configure datasets (references to objects in S3 buckets that will be mounted in user containers as files).
* The [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack), for supporting the "Argo Metrics" template (a template that automatically creates a Prometheus/Grafana stack for collecting metrics from Argo). We use [this](https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack) Helm chart.

To deploy, first add the repo and then install. For example:

```bash
helm repo add karvdash https://carv-ics-forth.github.io/karvdash/chart
helm install karvdash karvdash/karvdash --namespace default \
    --set karvdash.ingressURL=https://example.com \
    --set karvdash.stateHostPath=/mnt/nfs/karvdash \
    --set karvdash.filesURL=file:///mnt/nfs
```

Some of the variables set above are required. The table below lists all available options:

| Variable                            | Required | Description                                                                              | Default                           |
|-------------------------------------|----------|------------------------------------------------------------------------------------------|-----------------------------------|
| `image`                             |          | Docker image to use.                                                                     | `carvicsforth/karvdash:<version>` |
| `rbac.create`                       |          | Assign full permissions to Karvdash, API and namespace discovery to authenticated users. | `true`                            |
| `karvdash.stateVolumeClaim`         | &check;  | If set, use this persistent volume claim for storing state.                              |                                   |
| `karvdash.stateHostPath`            | &check;  | The host path to use for storing state, when no existing volume claim is set.            |                                   |
| `karvdash.logsVolumeClaim`          |          | The volume to store HTTP access and error logs.                                          |                                   |
| `karvdash.logsHostPath`             |          | The host path to use for storing logs, when no existing volume claim is set.             |                                   |
| `karvdash.djangoSecret`             |          | Secret for Django. Use a random string of 50 characters.                                 | autogenerated                     |
| `karvdash.djangoDebug`              |          | Set to anything to enable, empty to disable.                                             |                                   |
| `karvdash.adminPassword`            |          | The default admin password.                                                              | `admin`                           |
| `karvdash.htpasswdExportDir`        |          | If set, the path to export the htpasswd file in.                                         |                                   |
| `karvdash.dashboardTitle`           |          | The title of the dashboard.                                                              | `Dashboard`                       |
| `karvdash.dashboardTheme`           |          | The theme of the dashboard. Choose between "evolve" and "CARV".                          | `evolve`                          |
| `karvdash.issuesURL`                |          | If set, an option to "Report an issue" is shown in the user menu.                        |                                   |
| `karvdash.ingressURL`               | &check;  | The ingress URL used.                                                                    |                                   |
| `karvdash.dockerRegistryURL`        |          | The URL of the Docker registry.                                                          |                                   |
| `karvdash.dockerRegistryCert`       |          | The Docker registry certificate (use if self-signed).                                    |                                   |
| `karvdash.datasetsAvailable`        |          | Set to anything to enable dataset management.                                            |                                   |
| `karvdash.filesURL`                 | &check;  | The base URL for the private and shared file domains.                                    |                                   |
| `karvdash.filesSize`                |          | The size for the files persistent volume.                                                | `1Pi`                             |
| `karvdash.allowedHostPathDirs`      |          | Other host paths to allow attaching to containers (separate with `:`).                   |                                   |
| `karvdash.disabledServiceTemplates` |          | List of service templates to disable on deployment (filenames).                          |                                   |
| `karvdash.disabledDatasetTemplates` |          | List of dataset templates to disable on deployment (identifiers).                        |                                   |
| `karvdash.serviceURLPrefixes`       |          | List of predefined URL prefixes for services.                                            |                                   |
| `karvdash.argoURL`                  |          | Argo URL for integration with workflow frontend.                                         |                                   |
| `karvdash.argoNamespace`            |          | Argo namespace for service account managment.                                            |                                   |

Set `karvdash.filesURL` to:
* `file://<path>`, if using a node-wide, shared mountpoint for files.
* `nfs://<server>/<path>`, if using an NFS server for files.

Karvdash will create `private/<username>`, `shared`, and `uploads` folders within.

The state volume is used to store the database, the running services repository, and the template library. You can either use an existing peristent storage claim with `karvdash.stateVolumeClaim`, or set `karvdash.stateHostPath` to automatically create one (this must accessible by all nodes). Create a `templates` directory inside the state volume to add new service templates or override defaults (the ones in [templates](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/templates)). Templates placed there will be available as read-only to all users.

To remove Karvdash, uninstall using `helm uninstall karvdash`, which will remove the service, admission webhooks, and RBAC rules, but not associated CRDs. You can use the YAML files in [crds](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/chart/karvdash/crds) to remove them.

## Development

To develop Karvdash in a local Kubernetes environment, like the one provided by [Docker Desktop](https://www.docker.com/products/docker-desktop) for macOS (tested with [versions >= 2.5.x.x](https://docs.docker.com/docker-for-mac/release-notes/) which use Kubernetes 1.19.3), run:
```bash
make deploy-requirements
make prepare-develop
./manage.py runserver
```

This will setup all requirements (a private Docker registry, cert-manager, an SSL-enabled ingress controller, and Datashim) and set up a virtual environment to run Karvdash from the command line. You need to have [Helm](https://helm.sh) installed (version 3), as well as `mc` if using MinIO for files. When done, point your browser to http://127.0.0.1:8000 and login as "admin". Note, however, that when running Karvdash outside Kubernetes, there is no mutating admission webhook to attach file domains and datasets to service containers (use `make deploy-local` for running locally in a container).

Also, some versions of Docker Desktop [do not enforce RBAC rules](https://github.com/docker/for-mac/issues/3694), so there is no namespace isolation. Run the following commands to enable namespace isolation and explicitly set permissions for the `default` service account in the `default` namespace (used by Docker Desktop):
```bash
kubectl delete clusterrolebinding docker-for-desktop-binding
kubectl create clusterrolebinding default-cluster-admin --clusterrole=cluster-admin --serviceaccount=default:default
```

## Building images

Docker images for Karvdash are [available](https://hub.docker.com/r/carvicsforth/karvdash). To build your own locally, run:
```bash
make container
```

To change the version, edit `VERSION`. The image uses `kubectl` 1.19.8 by default, but this can be changed by setting the `KUBECTL_VERSION` variable before running `make`. You can also set your Docker account in `REGISTRY_NAME`.

To test the container in a local Kubernetes environment, run the following and then point your browser to https://localtest.me (provided by [localtest.me](https://readme.localtest.me)):
```bash
make deploy-local
```

To upload container images to Docker Hub, run:
```bash
make container-push
```

We use `buildx` to build the Karvdash container for multiple architectures (`linux/amd64` and `linux/arm64`).

To build and push additional service containers (custom Zeppelin-based containers):
```bash
make service-containers
make service-containers-push
```

## Acknowledgements

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 825061 (EVOLVE - [website](https://www.evolve-h2020.eu>), [CORDIS](https://cordis.europa.eu/project/id/825061)).
