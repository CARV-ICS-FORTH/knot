#!/bin/bash

# Disable swap
sed -e '/swap/ s/^#*/#/' -i /etc/fstab
swapoff -a

# Install Docker (https://docs.docker.com/engine/install/ubuntu/)
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
apt-mark hold docker-ce docker-ce-cli containerd.io

# Configure Docker (https://v1-22.docs.kubernetes.io/docs/setup/production-environment/container-runtimes/#docker)
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

# Install kubeadm (https://v1-22.docs.kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)
KUBERNETES_VERSION="1.22.4"
apt-get update
apt-get install -y apt-transport-https ca-certificates curl
curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet=${KUBERNETES_VERSION}-00 kubeadm=${KUBERNETES_VERSION}-00 kubectl=${KUBERNETES_VERSION}-00
apt-mark hold kubelet kubeadm kubectl

# Initialize Kubernetes (https://v1-22.docs.kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)
kubeadm init --pod-network-cidr=10.244.0.0/16 --kubernetes-version=${KUBERNETES_VERSION}
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/master-

# Install a Pod network add-on
FLANNEL_VERSION="0.15.1"
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/v${FLANNEL_VERSION}/Documentation/kube-flannel.yml

# Download and install Helm (https://helm.sh)
HELM_VERSION="3.8.0"
curl -LO https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz
tar -zxvf helm-v${HELM_VERSION}-linux-amd64.tar.gz
cp linux-amd64/helm /usr/local/bin/
rm -rf helm-v${HELM_VERSION}-linux-amd64.tar.gz linux-amd64
helm plugin install https://github.com/databus23/helm-diff

# Download and install Helmfile (https://github.com/roboll/helmfile)
HELMFILE_VERSION="0.143.0"
curl -LO https://github.com/roboll/helmfile/releases/download/v${HELMFILE_VERSION}/helmfile_linux_amd64
cp helmfile_linux_amd64 /usr/local/bin/helmfile
chmod +x /usr/local/bin/helmfile
rm -f helmfile_linux_amd64

# Install Knot
IP_ADDRESS=`ip -o route get 1 | sed -n 's/.*src \([0-9.]\+\).*/\1/p'`
export KNOT_HOST=${IP_ADDRESS}.nip.io
mkdir -p /mnt/state /mnt/state/jupyterhub /mnt/state/harbor/{database,redis,registry,chartmuseum,jobservice}
chown 1000:1000 /mnt/state/jupyterhub
chown 999:999 /mnt/state/harbor/{database,redis}
chown 10000:10000 /mnt/state/harbor/{registry,chartmuseum,jobservice}
mkdir -p /mnt/files
helmfile -f git::https://github.com/CARV-ICS-FORTH/knot.git@helmfile.yaml \
  --state-values-set ingress.service.type=NodePort \
  --state-values-set ingress.service.externalIPs\[0\]=${IP_ADDRESS} \
  --state-values-set storage.stateVolume.hostPath=/mnt/state \
  --state-values-set storage.filesVolume.hostPath=/mnt/files \
  sync
