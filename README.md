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

Having built the Docker image, go into `kubernetes` and run:
```
kubectl apply -k ./
```

The reverse is:
```
kubectl delete -k ./
```

Access locally at port `8000` with:
```
kubectl port-forward service/genome 8000:80
```
