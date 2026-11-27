# Kubernetes Guide: deploying the HR Assistant

This guide explains **what we deployed, why each piece exists, and how to talk about it**.
Every concept points to a file in `k8s/` so you can open the YAML while you explain it.

---

## 1. The 30-second explanation

> "I containerised the HR assistant with Docker and deployed it to a local Kubernetes cluster with kind.
> The FastAPI backend runs as a **Deployment** with 2 replicas behind a **ClusterIP Service**, with
> startup, liveness and readiness probes, resource requests/limits, zero-downtime rolling updates, a
> **PodDisruptionBudget** and a **HorizontalPodAutoscaler**. Postgres runs as a **StatefulSet** with a
> **PersistentVolumeClaim**, locked down by a **NetworkPolicy** so only the API can reach it. Config
> comes from a **ConfigMap**, credentials from a **Secret**. An **initContainer** waits for the DB and
> builds the vector index before the API starts, and the evaluation runs as a Kubernetes **Job**.
> The Streamlit UI is a second Deployment exposed through a **NodePort**. Because chat history lives
> in Postgres, the API pods are stateless and can scale horizontally."

---

## 2. Picture of what's running

```
                       your browser  http://localhost:8080
                                │
                    kind maps host 8080 → node 30080
                                │
┌─────────────────────── namespace: hr-assistant ────────────────────────────┐
│                               ▼                                            │
│   Service hr-ui (NodePort 30080) ──► Deployment hr-ui (1 pod, Streamlit)   │
│                                              │  http://hr-api  (DNS)       │
│                                              ▼                             │
│   Service hr-api (ClusterIP :80) ──► Deployment hr-api (2–5 pods, FastAPI) │
│        load-balances across READY pods        │   ▲ HPA scales on CPU      │
│                                               │   │ PDB keeps ≥1 up        │
│          each api pod:                        │                            │
│          initContainer wait-for-postgres      │                            │
│          initContainer build-index → emptyDir │                            │
│          container api (probes, limits)       │                            │
│                                               ▼  (NetworkPolicy: only api) │
│   Service postgres (headless) ──► StatefulSet postgres-0 ──► PVC data-0    │
│                                                                            │
│   ConfigMap hr-config   Secret hr-secrets   Job rag-eval (on demand)       │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Run it on your laptop

Prereqs: Docker Desktop (or Docker Engine), [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation), kubectl.

```bash
cd hr-knowledge-assistant
export GROQ_API_KEY=gsk_...        # optional; without it the offline mock LLM is used
./scripts/k8s-up.sh                # ~3–5 min the first time (image build)
open http://localhost:8080         # Streamlit UI
./scripts/k8s-demo.sh              # interactive tour of K8s behaviours (great to rehearse with)
./scripts/k8s-down.sh              # delete everything
```

Windows: run the scripts in Git Bash or WSL2.

> **Note:** I tested the manifests by rendering them (`kubectl kustomize k8s/`). I also ran the same image the
> way the pods run it: Postgres, the init-step ingest, then the API and UI as containers. The cloud sandbox
> I built this in could not run a nested Kubernetes cluster, so **do one full `k8s-up.sh` run on your machine
> before the interview**, and you'll have seen it work yourself.

---

## 4. Every object, explained (open the file while reading)

### Cluster (`k8s/kind-config.yaml`)
- **kind** = "Kubernetes IN Docker": each *node* is a Docker container. 1 control plane + 2 workers.
- **Control plane** runs the API server (everything talks to it), etcd (the key-value store holding all
  cluster state), the scheduler (picks a node for each pod) and the controller manager (the reconcile loops).
- **Worker nodes** run the kubelet (starts pods and runs the probes), kube-proxy (implements Services) and the container runtime (containerd).
- `extraPortMappings` maps host `8080` → node `30080`, so the NodePort is reachable without port-forward.

### Namespace (`00-namespace.yaml`)
A virtual partition. Everything for the app lives in `hr-assistant`, so you can apply RBAC/quotas per
namespace and clean up with one `kubectl delete ns hr-assistant`.

### ConfigMap (`01-configmap.yaml`)
Non-secret config (provider, top-k, threshold, paths, DB host) injected as env vars via `envFrom`.
This is the **12-factor** idea: the *same image* runs in dev/test/prod and only config changes.
Gotcha: editing a ConfigMap does **not** restart pods. Run `kubectl rollout restart deployment/hr-api` (or use a
checksum annotation / Reloader in real setups).

### Secret (`02-secret.yaml`)
DB password and LLM API keys. **Secrets are base64-*encoded*, not encrypted**. Anyone with read access can
decode them (`k8s-demo.sh` step 7 shows this). In production:
- enable etcd encryption at rest + tight RBAC,
- pull from a vault: **Azure Key Vault** (CSI driver / External Secrets Operator), AWS Secrets Manager, GCP Secret Manager,
- or Sealed Secrets so encrypted secrets can be committed to Git.

### StatefulSet + headless Service: Postgres (`10-postgres.yaml`)
- **Why StatefulSet, not Deployment?** Databases need a *stable identity* (`postgres-0`, always), a *stable
  DNS name* and their *own disk* that follows them. `volumeClaimTemplates` creates PVC `data-postgres-0`,
  which is re-attached if the pod is rescheduled.
- **Headless Service** (`clusterIP: None`): DNS returns the pod IP directly, with no virtual IP or load-balancing (you don't load-balance across DB replicas).
- **PVC / PV / StorageClass**: the PVC *requests* 1Gi; kind's default StorageClass (`local-path`)
  dynamically provisions a PV. Delete the pod and the data survives (demo step 8).
- `readinessProbe: pg_isready` → the pod only receives traffic once Postgres accepts connections.
- In the cloud you'd normally use a **managed DB** (Azure Database for PostgreSQL, Cloud SQL) instead.

### Deployment: API (`20-api.yaml`), the most important file
| Field | What it does | Why here |
|---|---|---|
| `replicas: 2` | ReplicaSet keeps 2 pods running | High availability; self-healing |
| `strategy.rollingUpdate maxSurge 1 / maxUnavailable 0` | New pod must be Ready before an old one is killed | Zero-downtime deploys |
| `initContainers` | Run to completion, in order, before the app | ① wait for Postgres ② build the Chroma index |
| `emptyDir` volume | Scratch dir shared by containers in the pod, deleted with the pod | Index built by init container, read by api |
| `envFrom` ConfigMap + Secret | All keys become env vars | 12-factor config |
| `$(VAR)` in `env` | Expands earlier env vars | Build `DATABASE_URL` from parts |
| `startupProbe` | Gives slow starters time (30×5 s) | Model loading; avoids premature liveness kills |
| `livenessProbe /health` | Failing ⇒ kubelet **restarts** the container | Recover from deadlocks/hangs |
| `readinessProbe /ready` | Failing ⇒ pod **removed from Service endpoints** | No traffic until the index is loaded + DB reachable |
| `resources.requests` | What the scheduler reserves | Placement + HPA % is relative to requests |
| `resources.limits` | Hard cap; CPU is throttled, memory ⇒ **OOMKilled** | Protect the node / neighbours |
| `securityContext runAsNonRoot` | Refuse to run as root | Least privilege (Dockerfile creates uid 10001) |
| `imagePullPolicy: IfNotPresent` | Use the image already on the node | kind: image is side-loaded with `kind load` |

**Liveness vs readiness (classic question):** liveness = "is it alive, or should I restart it?";
readiness = "should it receive traffic right now?". My `/health` is trivial (process up) and `/ready`
checks the DB and the vector index. Never make liveness depend on the DB, or a DB blip restarts every pod (a cascading failure).

**Why per-pod index (initContainer + emptyDir) instead of a shared volume?** It keeps pods **stateless and
independent**: no ReadWriteMany volume, no write contention on Chroma's SQLite files, so they scale freely.
The trade-off is that every new pod re-embeds the docs (fine for ~40 chunks; for big corpora use a vector DB
*service*: pgvector, Qdrant, Azure AI Search, and run ingestion as a Job/CronJob).

### Service: API (`20-api.yaml`)
ClusterIP: a stable virtual IP + DNS name `hr-api.hr-assistant.svc.cluster.local` (just `hr-api` from the same
namespace). kube-proxy load-balances to the **Ready** pods listed in its **Endpoints** (`kubectl get endpoints hr-api`).
Service types: **ClusterIP** (internal), **NodePort** (port on every node, 30000–32767), **LoadBalancer**
(cloud LB, e.g. on AKS/GKE), **Ingress** (L7 HTTP routing by host/path, TLS).

### PodDisruptionBudget (`20-api.yaml`)
`minAvailable: 1`. During *voluntary* disruptions (node drain, cluster upgrade) Kubernetes won't evict below 1 API pod.

### UI (`30-ui.yaml`)
Same image, different `command`. It talks to the API through the Service DNS name (`API_URL=http://hr-api`),
not an IP, because pod IPs change. Exposed as NodePort 30080.

### HPA (`40-hpa.yaml`)
Scales `hr-api` between 2 and 5 replicas to keep average CPU at **70% of requests**. Needs **metrics-server**
(the script installs it). Formula: `desired = ceil(current × currentUtil / targetUtil)`. The
`scaleDown.stabilizationWindowSeconds` setting prevents flapping. For LLM apps, CPU is a weak signal (time is spent *waiting* on the
LLM API); better signals are requests-in-flight or latency via custom metrics / **KEDA**.

### NetworkPolicy (`50-networkpolicy.yaml`)
By default every pod can talk to every pod. This policy says: pods labelled `app: postgres` accept
ingress **only** from `app: hr-api` on 5432. It needs a CNI that enforces policies (Calico, Cilium; recent kindnet).

### Job (`60-eval-job.yaml`)
Runs the RAG evaluation to completion (`restartPolicy: Never`, `backoffLimit: 1`, auto-deleted after an hour
via `ttlSecondsAfterFinished`). Deployment = keep running forever; Job = run once and finish; **CronJob** = Job on a schedule
(e.g. nightly re-ingestion of HR documents).

### Kustomize (`kustomization.yaml`)
`kubectl apply -k k8s/` applies all resources. Kustomize's real power is **overlays** (`base/` +
`overlays/dev`, `overlays/prod` patching replicas, image tags, resources) without templates. **Helm** is the
alternative: templated charts + packaging + release history.

---

## 5. What happens when you run `kubectl apply -k k8s/`? (great answer to practise)
1. kubectl renders the YAML and sends it to the **API server** (authn → authz/RBAC → admission controllers → validation).
2. The desired state is stored in **etcd**.
3. The **Deployment controller** creates a **ReplicaSet**; the ReplicaSet controller creates 2 **Pod** objects (unscheduled).
4. The **scheduler** picks a node for each pod (resource requests, taints/tolerations, affinity).
5. The **kubelet** on that node asks containerd to pull/start containers: init containers first, in order, then the app.
6. The kubelet runs the probes. When readiness passes, the **EndpointSlice controller** adds the pod IP to the Service.
7. **kube-proxy** (iptables/IPVS) on every node routes Service traffic to those endpoints; **CoreDNS** resolves `hr-api`.
8. Controllers keep **reconciling** forever: if a pod dies, actual (1) ≠ desired (2) → a new pod. This is the *declarative, desired-state* model.

---

## 6. Troubleshooting playbook (they love asking this)
| Symptom (`kubectl get pods`) | Meaning | How to debug |
|---|---|---|
| `Pending` | Not scheduled: not enough CPU/mem, PVC unbound, taints | `kubectl describe pod` → Events |
| `ImagePullBackOff` / `ErrImagePull` | Wrong image name/tag, private registry auth, (kind) image not loaded | `describe pod`; `kind load docker-image ...`; imagePullSecrets |
| `Init:0/2`, `Init:CrashLoopBackOff` | An init container is waiting/failing (e.g. DB not ready, ingest error) | `kubectl logs <pod> -c build-index` |
| `CrashLoopBackOff` | Container starts then exits, repeatedly (bad config, missing env, exception) | `kubectl logs <pod> --previous` |
| `Running` but `0/1 READY` | Readiness probe failing → no traffic | `describe pod` (probe failures), `curl /ready` via port-forward |
| `OOMKilled` (in describe, Last State) | Exceeded the memory limit | Raise limit / fix leak; check `kubectl top pod` |
| Service returns nothing | Selector labels don't match the pods, or no Ready pods | `kubectl get endpoints hr-api` (empty = selector/readiness issue) |

Core commands: `get`, `describe`, `logs [-f] [--previous] [-c container]`, `exec -it <pod> -- sh`,
`port-forward svc/hr-api 8000:80`, `get events --sort-by=.lastTimestamp`, `top pods`, `rollout status|history|undo`.

---

## 7. From kind to the cloud (JD mentions Azure / GCP)
| Local (kind) | Azure (AKS) | Google Cloud (GKE) |
|---|---|---|
| `kind load docker-image` | push to **Azure Container Registry** (`az acr build`), AKS pulls with managed identity | push to **Artifact Registry** |
| NodePort 30080 | Service `LoadBalancer` or **Ingress** (App Gateway / NGINX) + TLS via cert-manager | `LoadBalancer` / GKE Ingress |
| Secret in YAML | **Azure Key Vault** + CSI driver / workload identity | Secret Manager + Workload Identity |
| Postgres StatefulSet | Azure Database for PostgreSQL (Flexible Server) | Cloud SQL |
| Chroma in pod | **Azure AI Search** (vector + hybrid) or pgvector | Vertex AI Vector Search / AlloyDB pgvector |
| Groq/OpenAI | **Azure OpenAI** (same code: `LLM_PROVIDER=azure_openai`) | Vertex AI Gemini (`LLM_PROVIDER=gemini`) |
| metrics-server + HPA | same + cluster autoscaler (adds nodes) | same + node auto-provisioning |
| manual `kubectl apply` | CI/CD: GitHub Actions → build → push to ACR → `kubectl apply`/Helm, or GitOps with Argo CD/Flux | same |

---

## 8. Kubernetes interview questions, with answers

**Q: Docker vs Kubernetes?**
Docker builds and runs containers on one machine. Kubernetes *orchestrates* containers across many machines:
scheduling, self-healing, service discovery, scaling, rolling updates and config/secret management, all from declarative desired state.

**Q: Pod vs container vs Deployment vs ReplicaSet?**
Container = a process from an image. Pod = smallest deployable unit, 1+ containers sharing network namespace (localhost)
and volumes. ReplicaSet = keeps N identical pods running. Deployment = manages ReplicaSets to provide rolling updates
and rollbacks (each rollout creates a new ReplicaSet; `rollout undo` scales the old one back up).

**Q: Why not run the DB in a Deployment?**
Deployment pods are interchangeable with random names and no per-pod storage. A DB needs stable identity, stable
DNS and its own persistent volume, which is exactly what StatefulSet provides. Better still, use a managed DB in production.

**Q: How do pods find each other?**
Through Services + CoreDNS: `http://hr-api` → ClusterIP → kube-proxy → a ready pod. Never hard-code pod IPs, because they change on every restart.

**Q: How do you achieve zero-downtime deployments?**
RollingUpdate with `maxUnavailable: 0`, plus readiness probes (traffic only goes to ready pods), plus a PDB, plus graceful shutdown
(handle SIGTERM; `terminationGracePeriodSeconds`). Rollback with `kubectl rollout undo`.

**Q: Your API pods keep restarting. What do you do?**
`kubectl get pods` → `describe pod` (events, Last State: OOMKilled? exit code?) → `logs --previous`. Common
causes: liveness probe too aggressive (add a startupProbe), missing env/secret, OOM (raise limit), DB unreachable at boot.

**Q: Requests vs limits?**
Requests = guaranteed reservation used for scheduling. Limits = ceiling: CPU over the limit is *throttled*, memory over the limit is *OOMKilled*.
QoS classes: Guaranteed (req = lim), Burstable (mine), BestEffort (none; first to be evicted).

**Q: How would you scale this for 10,000 employees?**
Stateless API pods + HPA (ideally on in-flight requests via KEDA), the cluster autoscaler for nodes, an external
vector DB service instead of a per-pod index, a managed Postgres with connection pooling, caching of frequent answers
(e.g. Redis semantic cache), and rate limiting at the ingress. The LLM provider's rate limits usually become the bottleneck before Kubernetes does.

**Q: ConfigMap changed but the app didn't pick it up?**
Env vars are read at container start. `kubectl rollout restart deployment/hr-api`, or mount the ConfigMap as a volume (files
update in place) / add a config-hash annotation so a change triggers a rollout.

**Q: How do you keep secrets safe?**
RBAC on secrets, etcd encryption at rest, an external secret store (Key Vault) with workload identity, no secrets in images or Git,
and never logging env vars.

**Q: What is an Ingress?**
An L7 (HTTP) router with host/path rules and TLS termination, implemented by an Ingress Controller (NGINX, App Gateway, Traefik). One
public entry point can route `/api` → hr-api and `/` → hr-ui.

**Q: Helm vs Kustomize?**
Helm = templating + packaging + versioned releases (great for distributing apps). Kustomize = template-free overlays patching
plain YAML (built into kubectl). I used Kustomize because the app is small and I wanted plain, readable YAML.

**Q: What's a DaemonSet?**
One pod per node, used for node agents: log collectors (Fluent Bit), monitoring (node-exporter), CNI plugins. kube-proxy runs as one.

**Q: What would you add for production?**
An Ingress + TLS, external secrets, a managed DB, an image registry with vulnerability scanning, resource quotas, Prometheus/Grafana +
OpenTelemetry tracing, centralised logging, GitOps (Argo CD), and Helm/Kustomize overlays per environment.
