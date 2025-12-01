# kcpwd Kubernetes Usage Examples

Comprehensive real-world examples and use cases for kcpwd Kubernetes integration.

## Table of Contents

- [Quick Reference](#quick-reference)
- [CI/CD Pipelines](#cicd-pipelines)
- [GitOps Workflows](#gitops-workflows)
- [Development Workflows](#development-workflows)
- [Production Deployments](#production-deployments)
- [Multi-Environment Management](#multi-environment-management)
- [Helm Integration Examples](#helm-integration-examples)
- [Advanced Patterns](#advanced-patterns)
- [Security Best Practices](#security-best-practices)

---

## Quick Reference

### Basic Commands

```bash
# Store and sync
kcpwd set prod_db "password"
kcpwd k8s sync prod_db --namespace production

# Sync all
kcpwd k8s sync-all --namespace production

# Import from K8s
kcpwd k8s import db-credentials --namespace production

# Watch mode
kcpwd k8s watch --namespace production --interval 60
```

---

## CI/CD Pipelines

### 1. GitHub Actions - Basic Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy to Kubernetes
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install kcpwd
        run: pip install kcpwd
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
      
      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Sync secrets to K8s
        env:
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          API_KEY: ${{ secrets.API_KEY }}
          REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}
        run: |
          kcpwd set db_password "$DB_PASSWORD"
          kcpwd set api_key "$API_KEY"
          kcpwd set redis_password "$REDIS_PASSWORD"
          kcpwd k8s sync-all --namespace production
      
      - name: Deploy application
        run: kubectl apply -f k8s/deployment.yaml
      
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/myapp -n production
          kubectl get secrets -n production
```

### 2. GitHub Actions - Multi-Environment

```yaml
# .github/workflows/deploy-multi-env.yml
name: Multi-Environment Deploy

on:
  push:
    branches:
      - develop
      - staging
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
            echo "namespace=prod" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/staging" ]]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
            echo "namespace=staging" >> $GITHUB_OUTPUT
          else
            echo "environment=development" >> $GITHUB_OUTPUT
            echo "namespace=dev" >> $GITHUB_OUTPUT
          fi
      
      - name: Install kcpwd
        run: pip install kcpwd
      
      - name: Sync environment-specific secrets
        env:
          ENV: ${{ steps.env.outputs.environment }}
        run: |
          # Load environment-specific secrets
          kcpwd set ${ENV}_db_password "${{ secrets[format('{0}_DB_PASSWORD', steps.env.outputs.environment)] }}"
          kcpwd set ${ENV}_api_key "${{ secrets[format('{0}_API_KEY', steps.env.outputs.environment)] }}"
          
          # Sync with prefix
          kcpwd k8s sync-all \
            --namespace ${{ steps.env.outputs.namespace }} \
            --prefix ${ENV}_ \
            --label environment=${{ steps.env.outputs.environment }} \
            --label managed-by=github-actions
      
      - name: Deploy
        run: |
          kubectl apply -f k8s/${{ steps.env.outputs.environment }}/ \
            -n ${{ steps.env.outputs.namespace }}
```

### 3. GitLab CI - Complete Pipeline

```yaml
# .gitlab-ci.yml
stages:
  - secrets
  - deploy
  - verify

variables:
  NAMESPACE: ${CI_ENVIRONMENT_NAME}

sync-secrets:
  stage: secrets
  image: python:3.11-slim
  before_script:
    - pip install kcpwd
    - mkdir -p ~/.kube
    - echo "$KUBECONFIG" | base64 -d > ~/.kube/config
  script:
    # Store secrets
    - kcpwd set db_host "$DB_HOST"
    - kcpwd set db_password "$DB_PASSWORD"
    - kcpwd set db_user "$DB_USER"
    - kcpwd set api_key "$API_KEY"
    - kcpwd set jwt_secret "$JWT_SECRET"
    
    # Sync to K8s with labels
    - |
      kcpwd k8s sync-all \
        --namespace $NAMESPACE \
        --label app=myapp \
        --label environment=$CI_ENVIRONMENT_NAME \
        --label gitlab-pipeline=$CI_PIPELINE_ID
    
    # Verify
    - kubectl get secrets -n $NAMESPACE -l app=myapp
  only:
    - main
    - staging
    - develop

deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl apply -f k8s/ -n $NAMESPACE
    - kubectl rollout status deployment/myapp -n $NAMESPACE
  dependencies:
    - sync-secrets

verify:
  stage: verify
  image: curlimages/curl:latest
  script:
    - |
      # Wait for service to be ready
      sleep 10
      
      # Check health endpoint
      curl -f http://myapp.$NAMESPACE.svc.cluster.local/health
  dependencies:
    - deploy
```

### 4. Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        NAMESPACE = "${env.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip3 install kcpwd'
            }
        }
        
        stage('Sync Secrets') {
            steps {
                withCredentials([
                    string(credentialsId: 'db-password', variable: 'DB_PASSWORD'),
                    string(credentialsId: 'api-key', variable: 'API_KEY')
                ]) {
                    sh '''
                        kcpwd set db_password "$DB_PASSWORD"
                        kcpwd set api_key "$API_KEY"
                        kcpwd k8s sync-all --namespace $NAMESPACE
                    '''
                }
            }
        }
        
        stage('Deploy') {
            steps {
                sh 'kubectl apply -f k8s/ -n $NAMESPACE'
            }
        }
        
        stage('Verify') {
            steps {
                sh '''
                    kubectl rollout status deployment/myapp -n $NAMESPACE
                    kubectl get secrets -n $NAMESPACE
                '''
            }
        }
    }
    
    post {
        always {
            sh 'kcpwd k8s list --namespace $NAMESPACE --managed-only'
        }
    }
}
```

---

## GitOps Workflows

### 1. ArgoCD Integration

```yaml
# deployment.yaml (no secrets in git!)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:v1.0.0
        env:
        - name: DB_HOST
          value: "postgres.production.svc.cluster.local"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-password  # Created by kcpwd
              key: password
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-key  # Created by kcpwd
              key: password
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-password  # Created by kcpwd
              key: password
```

```bash
# Pre-sync hook script
#!/bin/bash
# sync-secrets.sh

set -e

echo "🔄 Syncing secrets to Kubernetes..."

# Sync secrets before ArgoCD deploys
kcpwd k8s sync-all --namespace production

echo "✓ Secrets synced successfully"
```

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
  # Pre-sync hook
  hooks:
  - name: sync-secrets
    hookType: PreSync
    script: |
      pip install kcpwd
      ./scripts/sync-secrets.sh
```

### 2. Flux Integration

```yaml
# flux/kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: myapp
  namespace: flux-system
spec:
  interval: 5m
  path: ./k8s
  prune: true
  sourceRef:
    kind: GitRepository
    name: myapp
  # Pre-build hook
  postBuild:
    substitute:
      NAMESPACE: production
```

```bash
# Flux secret sync script (run externally)
#!/bin/bash
# Run this periodically (e.g., via cron or K8s CronJob)

while true; do
    echo "$(date): Syncing secrets..."
    kcpwd k8s sync-all --namespace production
    
    # Trigger Flux reconciliation
    flux reconcile kustomization myapp
    
    sleep 300  # Every 5 minutes
done
```

### 3. Combined GitOps + kcpwd Watch

```bash
# Deploy kcpwd watch as a sidecar or separate pod

# Option 1: Kubernetes CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: kcpwd-sync
  namespace: production
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: kcpwd-sync
          containers:
          - name: sync
            image: python:3.11-slim
            command:
            - /bin/bash
            - -c
            - |
              pip install kcpwd
              kcpwd k8s sync-all --namespace production
          restartPolicy: OnFailure

---
# Option 2: Long-running Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kcpwd-watcher
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kcpwd-watcher
  template:
    metadata:
      labels:
        app: kcpwd-watcher
    spec:
      serviceAccountName: kcpwd-sync
      containers:
      - name: watcher
        image: python:3.11-slim
        command:
        - /bin/bash
        - -c
        - |
          pip install kcpwd
          kcpwd k8s watch --namespace production --interval 60
```

---

## Development Workflows

### 1. Local Development with Minikube

```bash
#!/bin/bash
# local-dev-setup.sh

set -e

echo "🚀 Setting up local K8s development environment..."

# Start Minikube
minikube start --memory 4096 --cpus 2

# Store development secrets locally
kcpwd set dev_db "postgres://localhost:5432/myapp_dev"
kcpwd set dev_redis "redis://localhost:6379"
kcpwd set dev_api_key "dev-api-key-12345"

# Sync to Minikube
kcpwd k8s sync-all --namespace dev --prefix dev_

# Deploy development stack
kubectl apply -f k8s/dev/

echo "✓ Local development environment ready!"
echo "📝 Access your app: minikube service myapp -n dev"
```

### 2. Kind (Kubernetes in Docker)

```bash
#!/bin/bash
# kind-setup.sh

# Create Kind cluster
kind create cluster --name kcpwd-dev

# Export kubeconfig
kubectl cluster-info --context kind-kcpwd-dev

# Setup dev secrets
cat <<EOF | kcpwd import /dev/stdin
{
  "passwords": [
    {"key": "dev_db_password", "password": "dev123"},
    {"key": "dev_api_key", "password": "dev-key"}
  ]
}
EOF

# Sync to Kind cluster
kcpwd k8s sync-all --namespace default

# Deploy
kubectl apply -f k8s/dev/

echo "✓ Kind cluster ready with secrets!"
```

### 3. Remote Development

```bash
# Remote dev environment (e.g., separate K8s cluster)

# Context switching
kubectl config use-context dev-cluster

# Developer-specific namespace
export DEV_NAMESPACE="dev-$(whoami)"

# Create namespace
kubectl create namespace $DEV_NAMESPACE

# Sync only your secrets
kcpwd k8s sync-all \
  --namespace $DEV_NAMESPACE \
  --label developer=$(whoami) \
  --label ephemeral=true

# Deploy your branch
kubectl apply -f k8s/ -n $DEV_NAMESPACE

# Cleanup when done
kubectl delete namespace $DEV_NAMESPACE
```

---

## Production Deployments

### 1. Blue-Green Deployment

```bash
#!/bin/bash
# blue-green-deploy.sh

set -e

CURRENT_ENV=$(kubectl get service myapp -n production -o jsonpath='{.spec.selector.version}')
NEW_ENV=$([[ "$CURRENT_ENV" == "blue" ]] && echo "green" || echo "blue")

echo "Current: $CURRENT_ENV, Deploying: $NEW_ENV"

# Deploy new version
kubectl apply -f k8s/production/deployment-${NEW_ENV}.yaml

# Sync secrets to new environment
kcpwd k8s sync-all \
  --namespace production \
  --label version=$NEW_ENV

# Wait for rollout
kubectl rollout status deployment/myapp-${NEW_ENV} -n production

# Run smoke tests
./scripts/smoke-test.sh $NEW_ENV

# Switch traffic
kubectl patch service myapp -n production -p '{"spec":{"selector":{"version":"'$NEW_ENV'"}}}'

echo "✓ Traffic switched to $NEW_ENV"

# Keep old version for quick rollback
echo "Old version ($CURRENT_ENV) still available for rollback"
```

### 2. Canary Deployment

```bash
#!/bin/bash
# canary-deploy.sh

set -e

# Deploy canary with 10% traffic
kubectl apply -f k8s/canary/

# Sync secrets
kcpwd k8s sync-all --namespace production --label version=canary

# Monitor for 10 minutes
echo "Monitoring canary for 10 minutes..."
sleep 600

# Check error rate
ERROR_RATE=$(kubectl logs -n production -l version=canary | grep ERROR | wc -l)

if [ $ERROR_RATE -lt 10 ]; then
    echo "✓ Canary successful, promoting to production"
    kubectl apply -f k8s/production/
    kcpwd k8s sync-all --namespace production --label version=stable
else
    echo "✗ Canary failed, rolling back"
    kubectl delete -f k8s/canary/
fi
```

### 3. Rolling Update with Secret Rotation

```bash
#!/bin/bash
# rolling-update-with-rotation.sh

set -e

echo "🔄 Starting rolling update with secret rotation..."

# Generate new password
NEW_PASSWORD=$(kcpwd generate -l 32 --print)

# Update password in kcpwd
kcpwd set db_password "$NEW_PASSWORD"

# Sync to K8s
kcpwd k8s sync db_password --namespace production

# Update database with new password
kubectl exec -n production deploy/db-admin -- \
  psql -c "ALTER USER myapp PASSWORD '$NEW_PASSWORD';"

# Rolling restart to pick up new secret
kubectl rollout restart deployment/myapp -n production

# Wait for completion
kubectl rollout status deployment/myapp -n production

echo "✓ Rolling update with secret rotation complete"
```

---

## Multi-Environment Management

### 1. Environment Isolation

```bash
#!/bin/bash
# setup-environments.sh

ENVIRONMENTS=("dev" "staging" "production")

for ENV in "${ENVIRONMENTS[@]}"; do
    echo "Setting up $ENV environment..."
    
    # Create namespace
    kubectl create namespace $ENV --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespace
    kubectl label namespace $ENV environment=$ENV --overwrite
    
    # Sync environment-specific secrets
    kcpwd k8s sync-all \
      --namespace $ENV \
      --prefix ${ENV}_ \
      --label environment=$ENV \
      --label managed-by=kcpwd
    
    echo "✓ $ENV environment ready"
done
```

### 2. Promotion Pipeline

```bash
#!/bin/bash
# promote-secrets.sh

set -e

FROM_ENV=$1
TO_ENV=$2

if [ -z "$FROM_ENV" ] || [ -z "$TO_ENV" ]; then
    echo "Usage: $0 <from-env> <to-env>"
    exit 1
fi

echo "🚀 Promoting secrets from $FROM_ENV to $TO_ENV..."

# List secrets from source environment
KEYS=$(kcpwd k8s list --namespace $FROM_ENV --managed-only | grep "  • " | awk '{print $2}')

for KEY in $KEYS; do
    echo "Promoting: $KEY"
    
    # Import from source K8s
    kcpwd k8s import $KEY --namespace $FROM_ENV --key ${TO_ENV}_${KEY}
    
    # Sync to target K8s
    kcpwd k8s sync ${TO_ENV}_${KEY} \
      --namespace $TO_ENV \
      --secret-name $KEY \
      --label promoted-from=$FROM_ENV
done

echo "✓ Promotion complete: $FROM_ENV → $TO_ENV"
```

### 3. Cross-Cluster Sync

```bash
#!/bin/bash
# sync-across-clusters.sh

set -e

SOURCE_CLUSTER="cluster-us-east"
TARGET_CLUSTER="cluster-eu-west"

echo "Syncing secrets from $SOURCE_CLUSTER to $TARGET_CLUSTER..."

# Switch to source cluster
kubectl config use-context $SOURCE_CLUSTER

# Import all secrets
kcpwd k8s import-all --namespace production

# Switch to target cluster
kubectl config use-context $TARGET_CLUSTER

# Sync to target
kcpwd k8s sync-all --namespace production

echo "✓ Cross-cluster sync complete"
```

---

## Helm Integration Examples

### 1. Basic Helm Chart with kcpwd

```yaml
# chart/values.yaml
database:
  host: "{{ kcpwd('db_host') }}"
  port: 5432
  name: myapp
  user: "{{ kcpwd('db_user') }}"
  password: "{{ kcpwd('db_password') }}"

api:
  endpoint: https://api.example.com
  key: "{{ kcpwd('api_key') }}"

redis:
  host: redis.default.svc.cluster.local
  password: "{{ kcpwd('redis_password') }}"

# Master-protected for production
production:
  secret: "{{ kcpwd('prod_secret', master=true) }}"
```

```bash
# Process and deploy
kcpwd helm template chart/values.yaml -o values-processed.yaml
helm install myapp ./chart -f values-processed.yaml --namespace production
```

### 2. Advanced Helm with Environments

```yaml
# chart/values-production.yaml
environment: production

database:
  host: "{{ kcpwd('prod_db_host') }}"
  password: "{{ kcpwd('prod_db_password', master=true) }}"

api:
  key: "{{ kcpwd('prod_api_key', master=true) }}"

# chart/values-staging.yaml
environment: staging

database:
  host: "{{ kcpwd('staging_db_host') }}"
  password: "{{ kcpwd('staging_db_password') }}"

api:
  key: "{{ kcpwd('staging_api_key') }}"
```

```bash
# Deploy to staging
kcpwd helm template chart/values-staging.yaml -o values-staging-processed.yaml
helm upgrade --install myapp ./chart \
  -f values-staging-processed.yaml \
  --namespace staging

# Deploy to production (will prompt for master password)
kcpwd helm template chart/values-production.yaml -o values-production-processed.yaml
helm upgrade --install myapp ./chart \
  -f values-production-processed.yaml \
  --namespace production
```

### 3. Helm + ArgoCD + kcpwd

```yaml
# argocd-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp-chart
    path: chart
    targetRevision: HEAD
    helm:
      valueFiles:
      - values-processed.yaml  # Pre-processed with kcpwd
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

```bash
# CI pipeline to process and commit
kcpwd helm template chart/values.yaml -o chart/values-processed.yaml
git add chart/values-processed.yaml
git commit -m "Update processed values"
git push

# ArgoCD will pick up changes
argocd app sync myapp
```

---

## Advanced Patterns

### 1. Secret Rotation Automation

```python
# secret_rotation.py
import schedule
import time
from datetime import datetime
from kcpwd import set_password, generate_password
from kcpwd.k8s import sync_to_k8s

def rotate_secret(key, namespace):
    """Rotate a secret automatically"""
    print(f"{datetime.now()}: Rotating {key}...")
    
    # Generate new password
    new_password = generate_password(length=32)
    
    # Update in kcpwd
    set_password(key, new_password)
    
    # Sync to K8s
    sync_to_k8s(key, namespace=namespace)
    
    # Trigger deployment restart
    import subprocess
    subprocess.run([
        "kubectl", "rollout", "restart",
        f"deployment/{key.replace('_', '-')}-app",
        "-n", namespace
    ])
    
    print(f"✓ {key} rotated successfully")

# Schedule rotations
schedule.every(30).days.do(rotate_secret, "db_password", "production")
schedule.every(7).days.do(rotate_secret, "api_key", "production")

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
```

### 2. Audit Logging

```python
# audit_logger.py
import json
from datetime import datetime
from kcpwd.k8s import K8sClient

class SecretAuditor:
    def __init__(self, log_file="secret_audit.log"):
        self.log_file = log_file
    
    def log_sync(self, key, namespace, action):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "namespace": namespace,
            "action": action,
            "user": os.getenv("USER", "unknown")
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_audit_trail(self, key=None):
        """Get audit trail for a specific key or all"""
        entries = []
        with open(self.log_file, "r") as f:
            for line in f:
                entry = json.loads(line)
                if key is None or entry["key"] == key:
                    entries.append(entry)
        return entries

# Usage
auditor = SecretAuditor()
auditor.log_sync("prod_db", "production", "sync")
print(auditor.get_audit_trail("prod_db"))
```

### 3. Backup and Disaster Recovery

```bash
#!/bin/bash
# backup-secrets.sh

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "📦 Backing up secrets..."

# Export from kcpwd
kcpwd export $BACKUP_DIR/kcpwd-backup.json

# Export K8s secrets
for NAMESPACE in dev staging production; do
    kubectl get secrets -n $NAMESPACE -o yaml > $BACKUP_DIR/k8s-${NAMESPACE}.yaml
done

# Encrypt backup
tar czf $BACKUP_DIR.tar.gz $BACKUP_DIR
gpg --encrypt --recipient ops@example.com $BACKUP_DIR.tar.gz

# Upload to S3
aws s3 cp $BACKUP_DIR.tar.gz.gpg s3://my-backups/secrets/

echo "✓ Backup complete: $BACKUP_DIR.tar.gz.gpg"
```

---

## Security Best Practices

### 1. RBAC Configuration

```yaml
# kcpwd-rbac.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kcpwd-sync
  namespace: production

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kcpwd-secret-manager
  namespace: production
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "create", "update", "patch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kcpwd-secret-manager
  namespace: production
subjects:
- kind: ServiceAccount
  name: kcpwd-sync
  namespace: production
roleRef:
  kind: Role
  name: kcpwd-secret-manager
  apiGroup: rbac.authorization.k8s.io
```

### 2. Namespace Isolation

```bash
# Strict namespace isolation
kubectl create namespace production
kubectl create namespace staging
kubectl create namespace dev

# Network policies
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-cross-namespace
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
EOF
```

### 3. Secret Encryption at Rest

```bash
# Enable encryption at rest in K8s
kubectl create -f - <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: $(head -c 32 /dev/urandom | base64)
    - identity: {}
EOF
```

---

## Troubleshooting

See [K8S_GUIDE.md](K8S_GUIDE.md#troubleshooting) for detailed troubleshooting guide.

---

**📚 More Resources:**
- [Main README](../README.md)
- [Kubernetes Guide](K8S_GUIDE.md)
- [API Documentation](API.md)

**💬 Questions?**
- [GitHub Discussions](https://github.com/osmanuygar/kcpwd/discussions)
- [Issue Tracker](https://github.com/osmanuygar/kcpwd/issues)