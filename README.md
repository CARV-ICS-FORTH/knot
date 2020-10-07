# Karvdash

Karvdash (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for working on a Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

Check out the user guide and API documentation in [docs](docs) (also available in Karvdash under "Documentation" at the user menu).

## Compatibility

We use Kubernetes 1.15.x to develop, test, and run Karvdash.

## Deployment

To deploy Karvdash you need a running Kubernetes environment with the following features:
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [xip.io](http://xip.io) if you don't have a DNS entry.
* A private Docker registry. You can deploy one using the [official instructions](https://docs.docker.com/registry/deploying/), or use [this](https://artifacthub.io/packages/helm/helm-stable/docker-registry) [Helm](https://helm.sh) chart.
* A shared filesystem mounted at the same path across all Kubernetes nodes, like NFS, [Gluster](https://www.gluster.org), or similar.

Then, you can set the following environmental variables and run `make deploy`.

| Variable                          | Description                                                                              |
|-----------------------------------|------------------------------------------------------------------------------------------|
| `KARVDASH_INGRESS_DOMAIN`         | The domain used (for example `example.com`).                                             |
| `KARVDASH_DOCKER_REGISTRY`        | The URL of the Docker registry (for example `https://username:password@127.0.0.1:5000`). |
| `KARVDASH_PERSISTENT_STORAGE_DIR` | The host path for Karvdash database, running service repository, and service templates.  |
| `KARVDASH_PRIVATE_HOST_DIR`       | The host path for the private file domain.                                               |
| `KARVDASH_SHARED_HOST_DIR`        | The host path for the shared file domain.                                                |

The directory variables should be set to some folder inside the shared mountpoint.

For example:
```bash
export KARVDASH_INGRESS_DOMAIN=example.com
export KARVDASH_DOCKER_REGISTRY=http://127.0.0.1:5000
export KARVDASH_PERSISTENT_STORAGE_DIR=/mnt/nfs/karvdash
export KARVDASH_PRIVATE_HOST_DIR=/mnt/nfs/private
export KARVDASH_SHARED_HOST_DIR=/mnt/nfs/shared
make deploy
```

This will install the necessary CRDs and use the variables to configure the `karvdash.yaml` template found in the `deploy` folder.

Depending on your setup, you may want to create a custom version of this template. To deploy the Karvdash Docker image, you must provide mount points for `/db` (persistent storage directory), `/private`, and `/shared`, and set any of the following variables:

| Variable                             | Description                                                                           |
|--------------------------------------|---------------------------------------------------------------------------------------|
| `DJANGO_SECRET`                      | Secret for Django. Use a random string of 50 characters.                              |
| `DJANGO_DEBUG`                       | Set to anything to enable, empty to disable (default is enabled).                     |
| `KARVDASH_ADMIN_PASSWORD`            | The default admin password (default is `admin`).                                      |
| `KARVDASH_SERVICE_TEMPLATE_DIR`      | The path to service templates (default is `/app/templates`)                           |
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

## Development

To work on Karvdash, you need a local Kubernetes environment, like Docker Desktop for macOS, with a running ingress controller and a local Docker registry (as you would on a bare metal setup).

Especially for Docker Desktop ([versions 2.2.x.x-2.3.x.x](https://docs.docker.com/docker-for-mac/release-notes/) use Kubernetes 1.15.5) running on macOS, these are all provided with `make deploy-docker-desktop`. This will setup an SSL-enabled ingress controller answering to https://localtest.me (provided by [localtest.me](https://readme.localtest.me)), start a private Docker registry (without SSL), and deploy Karvdash.

You can also install all the requirements with `make prepare-docker-desktop` and then run Karvdash locally.

First, create the Python environment:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create default directories for the database, private, and shared data:
```
mkdir db
mkdir private
mkdir shared
```

Prepare the application:
```
./manage.py migrate
./manage.py createadmin --noinput --username admin --password admin --email admin@example.com --preserve
```

And start it:
```
./manage.py runserver
```

Point your browser to http://localtest.me:8000 and login as "admin".

## Building images

To build the Karvdash Docker image:
```
make container
```

To upload to Docker Hub:
```
make push
```

## Acknowledgements

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 825061 (EVOLVE - [website](https://www.evolve-h2020.eu>), [CORDIS](https://cordis.europa.eu/project/id/825061)).
