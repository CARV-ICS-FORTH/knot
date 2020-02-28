# Local deployment in Docker Desktop

To deploy Genome in Kubernetes, you need a working ingress controller and a working Docker registry. Then you can start the Genome service and reach it at `localtest.me`. Each resource and service is defined in a separate YAML, so you can create and destroy them individually.

The following have been tested with *Docker Desktop for macOS*.

## Ingress

Deploy an [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/):
```
kubectl apply -f ingress-nginx.yaml
```

The YAML file contains a self-signed SSL certificate for the domain `localtest.me` (and the wildcard `*.localtest.me`).

To update the included certificate:
```
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout localtest.me.key -out localtest.me.crt -subj "/CN=*.localtest.me/CN=localtest.me/O=localtest.me"
kubectl create secret tls localtest.me --key localtest.me.key --cert localtest.me.crt
kubectl get secret localtest.me -o yaml
kubectl delete secret localtest.me
```

Copy the `tls.crt` and `tls.key` fields into `ingress-nginx.yaml` and reapply it.

## Docker registry

First create a 10 GB persistent volume claim for the registry and then create the service:
```
kubectl apply -f docker-registry-pvc.yaml
kubectl apply -f docker-registry.yaml
```

## Genome

Create a 1 GB persistent volume claim for Genome: and then create the service:
```
kubectl apply -f genome-pvc.yaml
```

Adjust the storage paths in `genome.yaml` and use your external IP in `GENOME_DOCKER_REGISTRY`. Then:
```
kubectl apply -f genome.yaml
```

## Other

You also need to apply some custom resource definitions:
```
kubectl apply -f argo.yaml
```
