#!/usr/bin/env bash
# A guided tour of Kubernetes behaviours to show (or practise explaining) in an interview.
set -uo pipefail
NS=hr-assistant
step() { echo; echo "### $*"; read -rp "(press enter)"; }

step "1. What is running? Pods, the node each landed on, and their IPs"
kubectl -n $NS get pods -o wide

step "2. Services give pods a stable DNS name + virtual IP. Endpoints = IPs of READY pods behind it"
kubectl -n $NS get svc,endpoints

step "3. Self-healing: delete an API pod. The ReplicaSet notices 1 < 2 replicas and creates a new one"
POD=$(kubectl -n $NS get pod -l app=hr-api -o jsonpath='{.items[0].metadata.name}')
kubectl -n $NS delete pod "$POD" --wait=false
sleep 2; kubectl -n $NS get pods -l app=hr-api

step "4. Manual scaling to 3 replicas"
kubectl -n $NS scale deployment/hr-api --replicas=3
kubectl -n $NS rollout status deployment/hr-api
kubectl -n $NS get pods -l app=hr-api

step "5. Zero-downtime rolling update (change an env var => new ReplicaSet), then roll back"
kubectl -n $NS set env deployment/hr-api TOP_K=5
kubectl -n $NS rollout status deployment/hr-api
kubectl -n $NS rollout history deployment/hr-api
kubectl -n $NS rollout undo deployment/hr-api
kubectl -n $NS rollout status deployment/hr-api

step "6. Call the API from INSIDE the cluster using the Service DNS name"
kubectl -n $NS run curl --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s -X POST http://hr-api/chat -H 'Content-Type: application/json' \
  -d '{"question":"How many sick leaves do I get?","employee_id":"E1001"}'

step "7. Config and secrets (values in a Secret are only base64 encoded!)"
kubectl -n $NS get configmap hr-config -o yaml | head -20
kubectl -n $NS get secret hr-secrets -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d; echo

step "8. Persistence: Postgres data lives on a PVC, so it survives the pod being deleted"
kubectl -n $NS get pvc
kubectl -n $NS delete pod postgres-0
kubectl -n $NS rollout status statefulset/postgres
kubectl -n $NS port-forward svc/hr-api 8000:80 >/dev/null 2>&1 & PF=$!; sleep 3
curl -s localhost:8000/tickets | head -c 300; echo; kill $PF

step "9. Autoscaler status and recent events"
kubectl -n $NS get hpa
kubectl -n $NS get events --sort-by=.lastTimestamp | tail -15

step "10. Run the evaluation as a Kubernetes Job"
kubectl delete -n $NS job rag-eval --ignore-not-found
kubectl apply -f k8s/60-eval-job.yaml
kubectl -n $NS wait --for=condition=complete job/rag-eval --timeout=300s
kubectl -n $NS logs job/rag-eval | tail -8
