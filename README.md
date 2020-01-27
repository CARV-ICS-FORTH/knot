# Genome

Genome is Evolve's integration dashboard. It supplies the landing page for working on the Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

## Running locally

To start working on Genome, first create the Python environment:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create default diretories for local and remote data (or set `GENOME_LOCAL_DIR` and `GENOME_REMOTE_DIR` environment variables):
```
mkdir local
mkdir remote
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
    -p 8000:8000/tcp \
    genome:latest
```

You can also override the `DJANGO_SECRET` with an environment variable.

## Run in Kubernetes

Having built the Docker image, go into `kubernetes` and edit `genome.yaml` to set the options according to your Kubernetes configuration. You need to adjust the storage paths and use your external cluster IP in `GENOME_DOCKER_REGISTRY`. You must also add this IP as an insecure Docker registry across all nodes in your cluster (see [here](https://docs.docker.com/registry/insecure/) for instructions).

Then run:
```
kubectl apply -k ./
```

The reverse is:
```
kubectl delete -k ./
```

Access Genome at your external cluster IP, at port `8000`.
