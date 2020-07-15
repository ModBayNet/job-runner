#!/bin/sh
set -e

export KUBECONFIG=/etc/deploy/config
mkdir -p /etc/deploy
echo ${KUBE_CONFIG_BASE64} | base64 -d >${KUBECONFIG}

cd /code/helm
helm dependency build

export RELEASE_NAME=modbay-web-worker
export DEPLOYS=$(helm ls | tail -n +2 | awk '{printf $1}{print $NF}' | grep "$RELEASE_NAME" | wc -l)

if [ ${DEPLOYS} -eq 0 ]; then
    helm install ${RELEASE_NAME} . --namespace=default
else
    helm upgrade ${RELEASE_NAME} . --namespace=default --set image.tag="$CI_COMMIT_SHA"
fi
