# Bare metal deployment

To deploy Karvdash in Kubernetes, you need a working cluster with an ingress controller (check [here](https://kubernetes.github.io/ingress-nginx/deploy/)) and - optionally - an accessible Docker registry (check [here](https://docs.docker.com/registry/deploying/)).

The files included here are templates. You need to edit them and fill in the appropriate IP addresses and paths. Then you can apply them one by one. Each resource and service is defined in a separate YAML, so you can create and destroy them individually.

Karvdash should run in the `default` namespace, assuming the corresponding service account has full permissions (or you need to adjust the permissions and the internal API base URL variable).

Create the Karvdash CRDs:
```
kubectl apply -f karvdash-crd.yaml
```

Create a 1 GB persistent volume and accompanying claim for Karvdash:
```
kubectl apply -f karvdash-pv.yaml
kubectl apply -f karvdash-pvc.yaml
```

Start the Karvdash service:
```
kubectl apply -f karvdash.yaml
```

And the mutating admission webhook configuration:
```
kubectl apply -f karvdash-maw.yaml
```

*The webhook template assumes that the dashboard runs with a verified SSL certificate. If you need an internal SSL proxy, check the local deployment instructions for Docker Desktop.*

You also need to apply some custom resource definitions for service templates used in Karvdash:
```
kubectl apply -f argo-crd.yaml
```

The Karvdash service will be reachable at the host specified at the ingress.
