# Karvdash

Karvdash (Kubernetes CARV dashboard) is a dashboard service for Kubernetes. It supplies the landing page for working on a Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

## Running locally

To start working on Karvdash, first create the Python environment:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create default directories for local, remote, and shared data:
```
mkdir local
mkdir remote
mkdir shared
```

Create necessary Kubernetes resources:
```
kubectl apply -f kubernetes/argo.yaml
```

Then run `start.sh`.

## Running in Docker

Edit `Dockerfile` and set the version of `kubectl` to match your Kubernetes cluster.

Build the image:
```
docker build -t karvdash .
```

Run it:
```
docker run -d --rm --name karvdash \
    --env KARVDASH_ADMIN_PASSWORD=admin \
    --mount type=bind,source=$PWD,destination=/db \
    --mount type=bind,source=$PWD/local,destination=/local \
    --mount type=bind,source=$PWD/remote,destination=/remote \
    --mount type=bind,source=$PWD/shared,destination=/shared \
    -p 8000:8000/tcp \
    karvdash:latest
```

The following variables can be set:

| Variable                        | Description                                                                           |
|---------------------------------|---------------------------------------------------------------------------------------|
| `DJANGO_SECRET`                 | Secret for Django. Use a random string of 50 characters.                              |
| `DJANGO_DEBUG`                  | Set to anything to enable, empty to disable (default is enabled).                     |
| `KARVDASH_ADMIN_PASSWORD`       | The default admin password (default is "admin").                                      |
| `KARVDASH_DASHBOARD_TITLE`      | The title of the dashboard (default is "Dashboard").                                  |
| `KARVDASH_DASHBOARD_THEME`      | The theme of the dashboard. Choose between "evolve" and "CARV" (default is "evolve"). |
| `KARVDASH_INGRESS_DOMAIN`       | The domain used by the service (default is "localtest.me").                           |
| `KARVDASH_SERVICE_REDIRECT_SSL` | Set to anything to redirect all services to SSL (default is disabled).                |
| `KARVDASH_DOCKER_REGISTRY`      | The URL of the Docker registry (default is "http://127.0.0.1").                       |
| `KARVDASH_LOCAL_HOST_DIR`       | The host path for the local data domain.                                              |
| `KARVDASH_REMOTE_HOST_DIR`      | The host path for the remote data domain.                                             |
| `KARVDASH_SHARED_HOST_DIR`      | The host path for the shared data domain.                                             |

## Run in Kubernetes

Deployment instructions are in the `kubernetes` folder, both for Docker Desktop and bare metal clusters.
