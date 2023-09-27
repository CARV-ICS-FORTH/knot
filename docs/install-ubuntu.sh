#!/bin/bash

# Disable swap
sed -e '/swap/ s/^#*/#/' -i /etc/fstab
swapoff -a

# Install Docker (https://docs.docker.com/engine/install/ubuntu/)
apt-get update
apt-get install -y ca-certificates curl gnupg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
apt-mark hold docker-ce docker-ce-cli containerd.io

# Configure Docker
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

# Install cri-dockerd (https://github.com/Mirantis/cri-dockerd)
CRI_DOCKERD_VERSION="0.3.4"
curl -LO https://github.com/Mirantis/cri-dockerd/releases/download/v${CRI_DOCKERD_VERSION}/cri-dockerd-${CRI_DOCKERD_VERSION}.$(dpkg --print-architecture).tgz
tar -zxvf cri-dockerd-${CRI_DOCKERD_VERSION}.$(dpkg --print-architecture).tgz
cp cri-dockerd/cri-dockerd /usr/local/bin/
rm -rf cri-dockerd-${CRI_DOCKERD_VERSION}.$(dpkg --print-architecture).tgz cri-dockerd
curl -Lo /etc/systemd/system/cri-docker.service https://raw.githubusercontent.com/Mirantis/cri-dockerd/v${CRI_DOCKERD_VERSION}/packaging/systemd/cri-docker.service
curl -Lo /etc/systemd/system/cri-docker.socket https://raw.githubusercontent.com/Mirantis/cri-dockerd/v${CRI_DOCKERD_VERSION}/packaging/systemd/cri-docker.socket
sed -i -e 's,/usr/bin/cri-dockerd,/usr/local/bin/cri-dockerd,' /etc/systemd/system/cri-docker.service
sed -i -e '/^ExecStart=/ s/$/ --pod-infra-container-image registry.k8s.io\/pause:3.9/' /etc/systemd/system/cri-docker.service
systemctl daemon-reload
systemctl enable --now cri-docker.socket

# Install kubeadm (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)
KUBERNETES_VERSION="1.28"
apt-get update
apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

# Initialize Kubernetes (https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)
kubeadm init --pod-network-cidr=10.244.0.0/16 --cri-socket unix:///var/run/cri-dockerd.sock
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# Install a Pod network add-on
FLANNEL_VERSION="0.22.3"
kubectl apply -f https://github.com/flannel-io/flannel/releases/download/v${FLANNEL_VERSION}/kube-flannel.yml

# Download and install Helm (https://helm.sh)
HELM_VERSION="3.12.3"
curl -LO https://get.helm.sh/helm-v${HELM_VERSION}-linux-$(dpkg --print-architecture).tar.gz
tar -zxvf helm-v${HELM_VERSION}-linux-$(dpkg --print-architecture).tar.gz
cp linux-$(dpkg --print-architecture)/helm /usr/local/bin/
rm -rf helm-v${HELM_VERSION}-linux-$(dpkg --print-architecture).tar.gz linux-$(dpkg --print-architecture)
helm plugin install https://github.com/databus23/helm-diff

# Download and install Helmfile (https://github.com/roboll/helmfile)
HELMFILE_VERSION="0.144.0"
curl -LO https://github.com/roboll/helmfile/releases/download/v${HELMFILE_VERSION}/helmfile_linux_$(dpkg --print-architecture)
cp helmfile_linux_$(dpkg --print-architecture) /usr/local/bin/helmfile
chmod +x /usr/local/bin/helmfile
rm -f helmfile_linux_$(dpkg --print-architecture)

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
