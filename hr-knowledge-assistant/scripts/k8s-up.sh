#!/usr/bin/env bash
# One command to run the whole stack on a local Kubernetes cluster (kind).
# Prereqs: docker, kind, kubectl.     Usage: ./scripts/k8s-up.sh
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER=hr-assistant
NS=hr-assistant

echo "==> 1/6 Create kind cluster (1 control-plane + 2 workers)"
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --config k8s/kind-config.yaml

echo "==> 2/6 Build the app image"
docker build -t hr-assistant:latest .

echo "==> 3/6 Load the image into the cluster nodes (no registry needed for kind)"
kind load docker-image hr-assistant:latest --name "$CLUSTER"

echo "==> 4/6 Install metrics-server (needed by the HPA)"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml >/dev/null
# kind's kubelets use self-signed certs
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' >/dev/null 2>&1 || true

echo "==> 5/6 Apply manifests"
kubectl apply -k k8s/
# Optional: put your LLM key into the Secret (otherwise the offline mock LLM is used)
if [[ -n "${GROQ_API_KEY:-}${OPENAI_API_KEY:-}${GOOGLE_API_KEY:-}" ]]; then
  kubectl -n "$NS" create secret generic hr-secrets \
    --from-literal=POSTGRES_PASSWORD=hr-password \
    --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
    --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    --from-literal=GOOGLE_API_KEY="${GOOGLE_API_KEY:-}" \
    --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$NS" rollout restart deployment/hr-api
fi

echo "==> 6/6 Wait for rollouts"
kubectl -n "$NS" rollout status statefulset/postgres --timeout=180s
kubectl -n "$NS" rollout status deployment/hr-api --timeout=300s
kubectl -n "$NS" rollout status deployment/hr-ui --timeout=180s
kubectl -n "$NS" get pods -o wide

cat <<MSG

Done!
  UI:   http://localhost:8080          (NodePort 30080 mapped by kind-config.yaml)
  API:  kubectl -n $NS port-forward svc/hr-api 8000:80   then open http://localhost:8000/docs
MSG
