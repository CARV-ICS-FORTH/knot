# Karvdash

Karvdash (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for working on a Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

Check out the user guide and API documentation in [docs](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/docs) (also available in Karvdash under "Documentation" at the user menu). Karvdash is written in [Python](https://www.python.org) using [Django](https://www.djangoproject.com).

![Karvdash services screen](https://github.com/CARV-ICS-FORTH/karvdash/raw/master/docs/images/services-screen.png)

## Compatibility

We use Kubernetes 1.19.x to develop, test, and run Karvdash.

Karvdash includes service templates for [Zeppelin](https://zeppelin.apache.org) 0.9.0, [Argo](https://argoproj.github.io/argo/) (both [Argo Workflows](https://github.com/argoproj/argo) 2.10.1 and [Argo Events](https://github.com/argoproj/argo-events) 1.0.0), and other applications.

The Zeppelin template uses a Karvdash-specific Docker image which adds `kubectl` 1.19.8, the `argo` utility (at the same version as the Argo service template), `karvdashctl` to manage Karvdash services from a notebook, [Spark](http://spark.apache.org) 2.4.5 with [Hadoop](https://hadoop.apache.org) 2.7, as well as the [evolve](https://bitbucket.org/sunlightio/evolve_python_library/) Python library from [Sunlight.io](https://sunlight.io), that allows building Argo workflows in Python.

The Zeppelin "with GPU support" template uses the above image with [CUDA](https://developer.nvidia.com/cuda-toolkit) 10.1 and [TensorFlow](http://www.tensorflow.org) 2.3.2 preinstalled, as well as the necessary directives to place the resulting container in a node with a GPU.

If your application requirements differ, you will need to create custom Docker images and service templates.

## Deployment

Karvdash is deployed using Helm [Helm](https://helm.sh) (version 3).

To install, you need a running Kubernetes environment with the following features:
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [xip.io](http://xip.io) if you don't have a DNS entry. We create the ingress using [this](https://artifacthub.io/packages/helm/ingress-nginx/ingress-nginx) Helm chart.
* A private Docker registry. You can run one using the [official instructions](https://docs.docker.com/registry/deploying/), or use [this](https://artifacthub.io/packages/helm/twuni/docker-registry) Helm chart.
* The [cert-manager](https://cert-manager.io) certificate management controller for Kubernetes. This is used for creating certificates automatically for the admission webhooks.
* A shared filesystem mounted at the same path across all Kubernetes nodes, like NFS, [Gluster](https://www.gluster.org), or similar.
* Optionally the [Dataset Lifecycle Framework](https://github.com/IBM/dataset-lifecycle-framework) deployed, in which case Karvdash can be used to configure datasets (the DLF should monitor all namespaces).

Also, make sure that the `default` service account in the `default` namespace (used by Karvdash), has administrator-level access to all namespaces, with:

```bash
kubectl create clusterrolebinding default-cluster-admin --clusterrole=cluster-admin --serviceaccount=default:default
```

To deploy, first add the repo and then install. For example:

```bash
helm repo add karvdash https://carv-ics-forth.github.io/karvdash
helm install karvdash karvdash/karvdash --namespace default \
    --set karvdash.ingressURL=https://example.com \
    --set karvdash.dockerRegistry=http://127.0.0.1:5000 \
    --set karvdash.persistentStorageDir=/mnt/nfs/karvdash \
    --set karvdash.filesURL=file:///mnt/nfs
```

Some of the variables set above are required. The table below lists all available options:

| Variable                          | Required | Description                                                            | Default                 |
|-----------------------------------|----------|------------------------------------------------------------------------|-------------------------|
| `image.namespace`                 |          | Namespace for Docker images.                                           | `carvicsforth`          |
| `image.tag`                       |          | Tag for Docker images.                                                 | latest version          |
| `rbac.create`                     |          | Include access-control rules for API and namespace discovery.          | `true`                  |
| `ingress.bodySize`                |          | The maximum allowed request size for the ingress.                      | `4096m`                 |
| `karvdash.persistentStorageDir`   | &check;  | The host path for persistent storage.                                  |                         |
| `karvdash.djangoSecret`           |          | Secret for Django. Use a random string of 50 characters.               | autogenerated           |
| `karvdash.djangoDebug`            |          | Set to anything to enable, empty to disable.                           |                         |
| `karvdash.adminPassword`          |          | The default admin password.                                            | `admin`                 |
| `karvdash.htpasswdExportDir`      |          | If set, the path to export the htpasswd file in.                       |                         |
| `karvdash.dashboardTitle`         |          | The title of the dashboard.                                            | `Dashboard`             |
| `karvdash.dashboardTheme`         |          | The theme of the dashboard. Choose between "evolve" and "CARV".        | `evolve`                |
| `karvdash.issuesURL`              |          | If set, an option to "Report an issue" is shown in the user menu.      |                         |
| `karvdash.ingressURL`             | &check;  | The ingress URL used.                                                  |                         |
| `karvdash.dockerRegistry`         |          | The URL of the Docker registry.                                        | `http://127.0.0.1:5000` |
| `karvdash.dockerRegistryNoVerify` |          | Set to anything to skip Docker registry SSL verification.              |                         |
| `karvdash.datasetsAvailable`      |          | Set to anything to enable dataset management.                          |                         |
| `karvdash.filesURL`               | &check;  | The base URL for the private and shared file domains.                  |                         |
| `karvdash.allowedHostPathDirs`    |          | Other host paths to allow attaching to containers (separate with `:`). |                         |


The required directory variables should be set to some folder inside the node-wide, shared mountpoint.

The host path for persistent storage is used to store the database, running services repository, and template library. Create a `templates` directory inside `karvdash.persistentStorageDir` to add new service templates or override defaults (the ones in [templates](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/templates)). Templates placed there will be available as read-only to all users.

To remove Karvdash, uninstall using `helm uninstall karvdash`, which will remove the service, admission webhooks, and RBAC rules, but not associated CRDs. You can use the YAML files in [crds](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/chart/karvdash/crds) to remove them.

## Development

To work on Karvdash, you need a local Kubernetes environment, with a running ingress controller, local Docker registry, and cert-manager (as you would on a bare metal setup).

Especially for [Docker Desktop](https://www.docker.com/products/docker-desktop) for macOS (tested with [versions >= 2.5.x.x](https://docs.docker.com/docker-for-mac/release-notes/) which use Kubernetes 1.19.3), these are all provided with `make deploy-docker-desktop`. This will setup an SSL-enabled ingress controller answering to https://localtest.me (provided by [localtest.me](https://readme.localtest.me)), start a private Docker registry (without SSL), install cert-manager, and deploy Karvdash. You need to have [Helm](https://helm.sh) installed (version 3).

Note that some versions of Docker Desktop [do not enforce RBAC rules](https://github.com/docker/for-mac/issues/3694), so there is no namespace isolation. Enable it by running `kubectl delete clusterrolebinding docker-for-desktop-binding`. You then need to explicitly set permissions for the `default` service account in the `default` namespace, with `kubectl create clusterrolebinding default-cluster-admin --clusterrole=cluster-admin --serviceaccount=default:default`.

You can also install all the requirements with `make prepare-docker-desktop` and then run Karvdash locally (note that when running Karvdash outside Kubernetes, there is no mutating admission webhook to attach file domains and datasets to service containers).

First, create the Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create default directories for private and shared data:
```bash
mkdir private
mkdir shared
```

Prepare the application:
```bash
./manage.py migrate
./manage.py createadmin --noinput --username admin --password admin --email admin@example.com --preserve
```

And start it:
```bash
./manage.py runserver
```

Point your browser to http://localtest.me:8000 and login as "admin".

## Building images

Docker images for Karvdash are [available](https://hub.docker.com/r/carvicsforth/karvdash). To build your own, run:
```bash
make container
```

Change the version by editing `VERSION`. The image uses `kubectl` 1.19.8 by default, but this can be changed by setting the `KUBECTL_VERSION` variable before running `make`. You can also set your Docker account in `REGISTRY_NAME`.

To upload to Docker Hub:
```bash
make container-push
```

To build and push additional service containers (custom Zeppelin-based containers):
```bash
make service-containers
make service-containers-push
```

## Acknowledgements

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 825061 (EVOLVE - [website](https://www.evolve-h2020.eu>), [CORDIS](https://cordis.europa.eu/project/id/825061)).
