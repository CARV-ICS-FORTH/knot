# Local deployment in Docker Desktop

To deploy Karvdash in Kubernetes as included with Docker Desktop, you need a working ingress controller and a working Docker registry. Then you can start the Karvdash service and reach it at http://localtest.me. Each resource and service is defined in a separate YAML, so you can create and destroy them individually.

Karvdash should run in the `default` namespace (or you need to adjust the permissions and the internal API base URL variable).

The following have been tested with *Docker Desktop for macOS*.

## Ingress

Deploy an [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/):
```
kubectl apply -f ingress-nginx.yaml
```

The YAML file contains a self-signed SSL certificate for the domain `localtest.me` and the wildcard `*.localtest.me`.

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

Optionally, apply `docker-registry-htpasswd.yaml` instead of `docker-registry.yaml` to use credentials (username: `admin`, password: `admin`).

## Karvdash

Create the Karvdash CRDs:
```
kubectl apply -f karvdash-crd.yaml
```

Create a 1 GB persistent volume claim for Karvdash:
```
kubectl apply -f karvdash-pvc.yaml
```

Adjust the storage paths in `karvdash.yaml` and use your external IP in `KARVDASH_DOCKER_REGISTRY`. You must also add this registry as an insecure Docker registry in the "Daemon" tab of the Docker Desktop application preferences.

Then:
```
kubectl apply -f karvdash.yaml
```

Karvdash should run in the `default` namespace (or at least a namespace with permissions to create other namespaces and service accounts).

## Karvdash Mutating Admission Webhook

If you are running Karvdash in debug mode, it will automatically attach user and shared volumes, as well as API configuration, to any service started.

However, when deploying Karvdash, you will need to create a mutating webhook configuration to filter API calls for attaching storage and configuration when creating pods and deployments. Kubernetes will only communicate with webhooks over HTTPS, using trusted certificates. As the Karvdash service will probably run internally, behind an ingress using the `localtest.me` self-signed certificate, you need a separate service acting as an HTTPS webhook proxy, with a certificate signed by your Kubernetes installation.

Build the webhook proxy Docker image:
```
(cd karvdash-maw/ssl && make cert)
(cd karvdash-maw && docker build -t karvdash-maw:1 .)
docker tag karvdash-maw:1 karvdash-maw:latest
```

Update the webhook service and configuration and apply:
```
sed -i '' "s/caBundle:.*/caBundle: $(cat karvdash-maw/ssl/karvdash-maw.pem | base64)/" karvdash-maw.yaml
kubectl apply -f karvdash-maw.yaml
```

## Other

You also need to apply some custom resource definitions for service templates used in Karvdash:
```
kubectl apply -f argo-crd.yaml
```

To enforce namespace isolation for service accounts, you may have to delete the `docker-for-desktop-binding` cluste role binding, with (details [here](https://github.com/docker/for-mac/issues/3694)):
```
delete clusterrolebinding docker-for-desktop-binding
```
