# Karvdash installation on bare metal

Install [Ubuntu Server 20.04 LTS](https://ubuntu.com/download/server) on a server with an external IP address (tested on [VirtualBox](https://www.virtualbox.org) with 2 CPUs, 4 GB RAM, bridged network adapter). Update packages. Run as root.

## System

Disable swap.

```bash
sed -e '/swap/ s/^#*/#/' -i /etc/fstab
swapoff -a
```

## Docker

Follow [these](https://docs.docker.com/engine/install/ubuntu/) instructions:

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
apt-mark hold docker-ce docker-ce-cli containerd.io
```

Follow [these](https://v1-22.docs.kubernetes.io/docs/setup/production-environment/container-runtimes/#docker) instructions:

```bash
mkdir -p /etc/docker
cat <<EOF | sudo tee /etc/docker/daemon.json
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF
systemctl enable docker
systemctl daemon-reload
systemctl restart docker
```

## Kubernetes

Follow [these](https://v1-22.docs.kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/) instructions:

```bash
KUBERNETES_VERSION="1.22.4"
apt-get update
apt-get install -y apt-transport-https ca-certificates curl
curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet=${KUBERNETES_VERSION}-00 kubeadm=${KUBERNETES_VERSION}-00 kubectl=${KUBERNETES_VERSION}-00
apt-mark hold kubelet kubeadm kubectl
```

Follow [these](https://v1-22.docs.kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/) instructions:

```bash
kubeadm init --pod-network-cidr=10.244.0.0/16 --kubernetes-version=${KUBERNETES_VERSION}
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/master-
```

Install a Pod network add-on:

```bash
FLANNEL_VERSION="0.15.1"
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/v${FLANNEL_VERSION}/Documentation/kube-flannel.yml
```

## Helm

Download and install the [Helm](https://helm.sh) binary:

```bash
HELM_VERSION="3.8.0"
curl -LO https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz
tar -zxvf helm-v${HELM_VERSION}-linux-amd64.tar.gz
cp linux-amd64/helm /usr/local/bin/
rm -rf helm-v${HELM_VERSION}-linux-amd64.tar.gz linux-amd64
helm plugin install https://github.com/databus23/helm-diff
```

## Helmfile

Download and install the [Helmfile](https://github.com/roboll/helmfile) binary:

```bash
HELMFILE_VERSION="0.143.0"
curl -LO https://github.com/roboll/helmfile/releases/download/v${HELMFILE_VERSION}/helmfile_linux_amd64
cp helmfile_linux_amd64 /usr/local/bin/helmfile
rm -f helmfile_linux_amd64
```

## Karvdash

Clone and deploy [Karvdash](https://github.com/CARV-ICS-FORTH/karvdash):

```bash
git clone https://github.com/CARV-ICS-FORTH/karvdash.git
cd karvdash
apt-get install -y make
IP_ADDRESS=`ip -o route get 1 | sed -n 's/.*src \([0-9.]\+\).*/\1/p'`
BAREMETAL=yes IP_ADDRESS=$IP_ADDRESS make deploy-requirements
BAREMETAL=yes IP_ADDRESS=$IP_ADDRESS make deploy-local
```
