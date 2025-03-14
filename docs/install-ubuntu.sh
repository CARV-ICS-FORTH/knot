#!/bin/bash

# Install Kubernetes and Knot on Ubuntu 24.04 LTS

# Disable swap
sed -e '/swap/ s/^#*/#/' -i /etc/fstab
swapoff -a

# Load modules
cat <<EOF | tee /etc/modules-load.d/k8s.conf
br_netfilter
EOF
modprobe br_netfilter

# Prepare for the container runtime (https://kubernetes.io/docs/setup/production-environment/container-runtimes/)
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.ipv4.ip_forward = 1
EOF
sysctl --system

# Install containerd (https://docs.docker.com/engine/install/ubuntu/)
apt-get update
apt-get install ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install containerd.io
apt-mark hold containerd.io

# Configure containerd (enable CRI integration plugin, set cgroup driver to systemd)
mv /etc/containerd/config.toml /etc/containerd/config.toml.default
containerd config default \
  | sed 's/SystemdCgroup = false/SystemdCgroup = true/' \
  | sed 's/pause\:3.8/pause\:3.10/' \
  | tee /etc/containerd/config.toml
systemctl restart containerd

# Install kubeadm (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)
KUBERNETES_VERSION="1.31"
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

# Initialize Kubernetes (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)
kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# Install a Pod network add-on
FLANNEL_VERSION="0.26.5"
kubectl apply -f https://github.com/flannel-io/flannel/releases/download/v${FLANNEL_VERSION}/kube-flannel.yml

# Download and install Helm (https://helm.sh)
HELM_VERSION="3.17.2"
curl -LO https://get.helm.sh/helm-v${HELM_VERSION}-linux-$(dpkg --print-architecture).tar.gz
tar -zxvf helm-v${HELM_VERSION}-linux-$(dpkg --print-architecture).tar.gz
cp linux-$(dpkg --print-architecture)/helm /usr/local/bin/
rm -rf helm-v${HELM_VERSION}-linux-$(dpkg --print-architecture).tar.gz linux-$(dpkg --print-architecture)
apt-get install -y git
helm plugin install https://github.com/databus23/helm-diff

# Download and install Helmfile (https://github.com/roboll/helmfile)
HELMFILE_VERSION="0.171.0"
curl -LO https://github.com/helmfile/helmfile/releases/download/v${HELMFILE_VERSION}/helmfile_${HELMFILE_VERSION}_linux_$(dpkg --print-architecture).tar.gz
tar zxvf helmfile_${HELMFILE_VERSION}_linux_$(dpkg --print-architecture).tar.gz helmfile
cp helmfile /usr/local/bin/
rm -f helmfile_${HELMFILE_VERSION}_linux_$(dpkg --print-architecture).tar.gz helmfile

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
