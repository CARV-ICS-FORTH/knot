# Karvdash

Karvdash (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for working on a Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

Check out the user guide and API documentation in [docs](docs) (also available in Karvdash under "Documentation" at the user menu). Karvdash is written in [Python](https://www.python.org) using [Django](https://www.djangoproject.com).

![Karvdash services screen](docs/images/services-screen.png)

## Compatibility

We use Kubernetes 1.15.x to develop, test, and run Karvdash.

Karvdash includes service templates for [Zeppelin](https://zeppelin.apache.org) 0.9.0, [Argo](https://argoproj.github.io/argo/) (both [Argo Workflows](https://github.com/argoproj/argo) 2.10.1 and [Argo Events](https://github.com/argoproj/argo-events) 1.0.0), and other applications.

The Zeppelin template uses a Karvdash-specific Docker image which adds `kubectl` 1.15.10, the `argo` utility (at the same version as the Argo service template), `karvdashctl` to manage Karvdash services from a notebook, as well as [Spark](http://spark.apache.org) 2.4.5 with [Hadoop](https://hadoop.apache.org) 2.7.

The Zeppelin "with GPU support" template uses the above image with [CUDA](https://developer.nvidia.com/cuda-toolkit) 10.1 and [TensorFlow](http://www.tensorflow.org) 2.2.1 preinstalled, as well as the necessary directives to place the resulting container in a node with a GPU.

If your application requirements differ, you will need to create custom Docker images and service templates.

## Deployment

To deploy Karvdash you need a running Kubernetes environment with the following features:
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [xip.io](http://xip.io) if you don't have a DNS entry.
* A private Docker registry. You can deploy one using the [official instructions](https://docs.docker.com/registry/deploying/), or use [this](https://artifacthub.io/packages/helm/helm-stable/docker-registry) [Helm](https://helm.sh) chart.
* A shared filesystem mounted at the same path across all Kubernetes nodes, like NFS, [Gluster](https://www.gluster.org), or similar.
* Optionally the [Dataset Lifecycle Framework](https://github.com/IBM/dataset-lifecycle-framework) deployed, in which case Karvdash can be used to configure datasets (the DLF should monitor all namespaces).

Also, make sure that the `default` service account in the `default` namespace (used by Karvdash), has administrator-level access to all namespaces, with `kubectl create clusterrolebinding default-cluster-admin --clusterrole=cluster-admin --serviceaccount=default:default`.

Then, you can set the following environmental variables and run `make deploy`.

| Variable                          | Description                                                                                     |
|-----------------------------------|-------------------------------------------------------------------------------------------------|
| `KARVDASH_INGRESS_DOMAIN`         | The domain used (for example `example.com`).                                                    |
| `KARVDASH_DOCKER_REGISTRY`        | The URL of the Docker registry (for example `https://username:password@127.0.0.1:5000`).        |
| `KARVDASH_DATASETS_AVAILABLE`     | Set to anything to enable dataset management (default is disabled).                             |
| `KARVDASH_PERSISTENT_STORAGE_DIR` | The host path for persistent storage (database, running services repository, template library). |
| `KARVDASH_PRIVATE_HOST_DIR`       | The host path for the private file domain.                                                      |
| `KARVDASH_SHARED_HOST_DIR`        | The host path for the shared file domain.                                                       |

The directory variables should be set to some folder inside the node-wide, shared mountpoint.

For example:
```bash
export KARVDASH_INGRESS_DOMAIN=example.com
export KARVDASH_DOCKER_REGISTRY=http://127.0.0.1:5000
export KARVDASH_PERSISTENT_STORAGE_DIR=/mnt/nfs/karvdash
export KARVDASH_PRIVATE_HOST_DIR=/mnt/nfs/private
export KARVDASH_SHARED_HOST_DIR=/mnt/nfs/shared
make deploy
```

This will install the necessary CRDs and use the variables to configure the `karvdash.yaml` template found in the [deploy](deploy/) folder.

Create a `templates` directory inside `KARVDASH_PERSISTENT_STORAGE_DIR` to add new templates or override defaults (the ones in [templates](templates/)). Templates placed there will be available as read-only to all users.

Depending on your setup, you may want to create a custom version of `karvdash.yaml`. To deploy the Karvdash Docker image, you must provide mount points for `/db` (persistent storage directory), `/private`, and `/shared`, and set the following variables:

| Variable                             | Description                                                                           |
|--------------------------------------|---------------------------------------------------------------------------------------|
| `DJANGO_SECRET`                      | Secret for Django. Use a random string of 50 characters.                              |
| `DJANGO_DEBUG`                       | Set to anything to enable, empty to disable (default is enabled).                     |
| `KARVDASH_ADMIN_PASSWORD`            | The default admin password (default is `admin`).                                      |
| `KARVDASH_HTPASSWD_EXPORT_DIR`       | If set, the path to export the htpasswd file in.                                      |
| `KARVDASH_DASHBOARD_TITLE`           | The title of the dashboard (default is `Dashboard`).                                  |
| `KARVDASH_DASHBOARD_THEME`           | The theme of the dashboard. Choose between "evolve" and "CARV" (default is `evolve`). |
| `KARVDASH_ISSUES_URL`                | If set, an option to "Report an issue" is shown in the user menu.                     |
| `KARVDASH_INGRESS_DOMAIN`            | The domain used (default is `localtest.me`).                                          |
| `KARVDASH_SERVICE_REDIRECT_SSL`      | Set to anything to redirect all services to SSL (default is disabled).                |
| `KARVDASH_DOCKER_REGISTRY`           | The URL of the Docker registry (default is `http://127.0.0.1:5000`).                  |
| `KARVDASH_DOCKER_REGISTRY_NO_VERIFY` | Set to anything to skip Docker registry SSL verification (default is to verify).      |
| `KARVDASH_DATASETS_AVAILABLE`        | Set to anything to enable dataset management (default is disabled).                   |
| `KARVDASH_API_BASE_URL`              | The URL used for internal API calls (default is `http://karvdash.default.svc/api`).   |
| `KARVDASH_PRIVATE_HOST_DIR`          | The host path for the private file domain.                                            |
| `KARVDASH_SHARED_HOST_DIR`           | The host path for the shared file domain.                                             |

To remove Karvdash, run `make undeploy`, which will remove the service and mutating admission webhook, but not associated CRDs and additional RBAC rules. Use `make undeploy-crds` for explicitly removing CRDs and any stored data, and `make undeploy-rbac` for removing RBAC rules.

## Development

To work on Karvdash, you need a local Kubernetes environment, with a running ingress controller and a local Docker registry (as you would on a bare metal setup).

Especially for [Docker Desktop](https://www.docker.com/products/docker-desktop) for macOS ([versions 2.2.x.x-2.3.x.x](https://docs.docker.com/docker-for-mac/release-notes/) use Kubernetes 1.15.5), these are all provided with `make deploy-docker-desktop`. This will setup an SSL-enabled ingress controller answering to https://localtest.me (provided by [localtest.me](https://readme.localtest.me)), start a private Docker registry (without SSL), and deploy Karvdash.

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
make containers
```

Change the version by editing `VERSION`. The images use `kubectl` 1.15.10 by default, but this can be changed by setting the `KUBECTL_VERSION` variable before running `make`. You can also set your Docker account in `REGISTRY_NAME`.

To upload to Docker Hub:
```bash
make containers-push
```

To build and push additional service containers (custom Zeppelin-based containers):
```bash
make service-containers
make service-containers-push
```

## Acknowledgements

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 825061 (EVOLVE - [website](https://www.evolve-h2020.eu>), [CORDIS](https://cordis.europa.eu/project/id/825061)).
