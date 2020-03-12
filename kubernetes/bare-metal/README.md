# Bare metal deployment

To deploy Genome in Kubernetes, you need a working cluster with an ingress controller (check [here](https://kubernetes.github.io/ingress-nginx/deploy/)) and - optionally - an accessible Docker registry (check [here](https://docs.docker.com/registry/deploying/)).

The files included here are templates. You need to edit them and fill in the appropriate IP addresses and paths. Then you can apply them one by one. Each resource and service is defined in a separate YAML, so you can create and destroy them individually.

Create a 1 GB persistent volume and accompanying claim for Genome:
```
kubectl apply -f genome-pv.yaml
kubectl apply -f genome-pvc.yaml
```

Start the Genome service:
```
kubectl apply -f genome.yaml
```

You also need to apply some custom resource definitions for service templates (Genes) used in Genome:
```
kubectl apply -f argo.yaml
```

The Genome service will be reachable at the host specified at the ingress.
