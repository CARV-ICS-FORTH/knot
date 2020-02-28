# Genome

Genome is Evolve's integration dashboard. It supplies the landing page for working on the Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

## Running locally

To start working on Genome, first create the Python environment:
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
docker build -t genome .
```

Run it:
```
docker run -d --rm --name genome \
    --env GENOME_ADMIN_PASSWORD=admin \
    --mount type=bind,source=$PWD,destination=/db \
    --mount type=bind,source=$PWD/local,destination=/local \
    --mount type=bind,source=$PWD/remote,destination=/remote \
    --mount type=bind,source=$PWD/shared,destination=/shared \
    -p 8000:8000/tcp \
    genome:latest
```

You can also override the `DJANGO_SECRET` with an environment variable.

## Run in Kubernetes

Deployment instructions are in the `kubernetes` folder.

Genome should run in the `default` namespace.
