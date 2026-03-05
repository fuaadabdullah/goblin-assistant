# 🚀 Production Deployment Checklist

## Pre-Deployment Preparation

### 🔐 Security & Secrets
- [ ] Generate strong API key: `openssl rand -base64 32`
- [ ] Create dedicated AWS IAM user for S3 access
- [ ] Set up MinIO with proper authentication
- [ ] Configure TPM/GCP Shielded VM attestation (if available)
- [ ] Set up TLS certificates via cert-manager
- [ ] Configure external DNS for ingress

### 📊 Monitoring Setup
- [ ] Deploy Prometheus Operator in cluster
- [ ] Configure Grafana with proper authentication
- [ ] Set up AlertManager with notification channels
- [ ] Configure log aggregation (ELK/EFK stack)
- [ ] Set up metrics retention policies

### 🏗️ Infrastructure Requirements
- [ ] Kubernetes cluster with version 1.24+
- [ ] NGINX Ingress Controller installed
- [ ] cert-manager for TLS certificate management
- [ ] Docker runtime available on nodes
- [ ] Sufficient resources (CPU: 2+, Memory: 4GB+ per node)

## Deployment Commands

### 1. Create Production Secrets
```bash
# Update production secrets with secure values
kubectl apply -f k8s/production-secrets.yaml

# Verify secrets are created
kubectl get secrets -n sandbox
```

### 2. Deploy Sandbox Components
```bash
# Run the automated deployment script
chmod +x k8s/deploy.sh
./k8s/deploy.sh

# Or deploy manually step-by-step:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/scaling.yaml
kubectl apply -f k8s/user-namespaces.yaml
kubectl apply -f k8s/gvisor-runtime.yaml
kubectl apply -f k8s/attestation-webhook.yaml
```

### 3. Configure External Access
```bash
# Deploy ingress with TLS
kubectl apply -f k8s/ingress.yaml

# Wait for certificates to be issued
kubectl get certificates -n sandbox
kubectl get certificate attestation-webhook-cert -n sandbox
```

### 4. Set up Monitoring
```bash
# Import Grafana dashboard
curl -X POST -H "Content-Type: application/json" \
  -d @grafana-dashboard.json \
  http://grafana.yourdomain.com/api/dashboards/db

# Verify Prometheus metrics collection
kubectl get servicemonitors -n sandbox

# Check alerting rules
kubectl get prometheusrules -n monitoring
```

## Post-Deployment Verification

### 🔍 Health Checks
```bash
# Check all pods are running
kubectl get pods -n sandbox

# Verify API health
curl -k https://sandbox.yourdomain.com/health

# Check metrics endpoint
curl -k https://sandbox.yourdomain.com/api/v1/sandbox/metrics

# Test sandbox functionality
curl -X POST https://sandbox.yourdomain.com/api/v1/sandbox/submit \
  -H "X-API-Key: your-production-api-key" \
  -H "Content-Type: application/json" \
  -d '{"language": "python", "source": "print(\"Hello from secure sandbox!\")"}'
```

### 📊 Monitoring Verification
```bash
# Check Grafana dashboard loads
open https://grafana.yourdomain.com/d/sandbox-security-dashboard

# Verify Prometheus targets
kubectl get targets -n monitoring

# Check alerting rules are loaded
kubectl get prometheusrules -n monitoring
```

### 🔒 Security Verification
```bash
# Verify Pod Security Standards
kubectl get pods -n sandbox -o jsonpath='{.items[*].spec.securityContext}'

# Check network policies
kubectl get networkpolicies -n sandbox

# Verify RBAC
kubectl get roles,rolebindings -n sandbox

# Test attestation (if configured)
kubectl get pods -n sandbox -l app=attestation-webhook
```

## Production Operations

### 🔄 Scaling Operations
```bash
# Scale workers based on load
kubectl scale deployment goblin-assistant-worker -n sandbox --replicas=3

# Update API resources
kubectl set resources deployment goblin-assistant-api -n sandbox \
  --requests=cpu=200m,memory=256Mi \
  --limits=cpu=1000m,memory=1Gi
```

### 🔧 Maintenance Operations
```bash
# Rolling update of API
kubectl rollout restart deployment/goblin-assistant-api -n sandbox

# Update secrets (zero-downtime)
kubectl create secret generic sandbox-secrets-new --from-literal=api-key=new-key --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/goblin-assistant-api -n sandbox
kubectl delete secret sandbox-secrets
kubectl rename secret sandbox-secrets-new sandbox-secrets
```

### 📈 Monitoring & Alerting
```bash
# Check current queue depth
kubectl exec -n sandbox deployment/goblin-assistant-api -- curl localhost:8001/sandbox/metrics | grep queue_depth

# View active alerts
kubectl get alerts -n monitoring

# Check SLO compliance
# (Monitor via Grafana dashboard)
```

## Disaster Recovery

### 🔄 Backup Procedures
```bash
# Redis backup
kubectl exec redis-pod -n sandbox -- redis-cli save
kubectl cp redis-pod:/data/appendonly.aof ./redis-backup-$(date +%Y%m%d).aof

# MinIO backup
mc mirror minio-service/goblin-sandbox ./minio-backup-$(date +%Y%m%d)/
```

### 🛟 Recovery Procedures
```bash
# Restore from backup
kubectl cp ./redis-backup-20240117.aof redis-pod:/data/appendonly.aof
kubectl exec redis-pod -n sandbox -- redis-cli shutdown nosave
# Pod will restart automatically

# MinIO restore
mc mirror ./minio-backup-20240117/ minio-service/goblin-sandbox
```

## Security Compliance

### ✅ CIS Kubernetes Benchmarks
- [x] Pod Security Standards enforced
- [x] RBAC implemented with minimal permissions
- [x] Network policies configured
- [x] Secrets management implemented
- [x] Audit logging enabled

### ✅ Container Security
- [x] Non-root user execution
- [x] Read-only root filesystem
- [x] No privilege escalation
- [x] Resource limits enforced
- [x] Image signature verification (optional)

### ✅ Runtime Security
- [x] syscall filtering (gVisor)
- [x] User namespace isolation
- [x] Hardware-backed attestation
- [x] Admission controller validation

## Emergency Contacts

- **Platform Team**: platform@yourcompany.com
- **Security Team**: security@yourcompany.com
- **On-call Engineer**: oncall@yourcompany.com
- **Vendor Support**: support@goblin-assistant.com

## Rollback Plan

If deployment fails:
1. Roll back to previous version: `kubectl rollout undo deployment/goblin-assistant-api -n sandbox`
2. Check logs: `kubectl logs -n sandbox deployment/goblin-assistant-api --previous`
3. Alert team and investigate root cause
4. Update deployment checklist with lessons learned

---

**🎯 Deployment Status**: Ready for production
**🔒 Security Level**: Enterprise-grade
**📊 Monitoring**: Comprehensive
**🛟 Support**: 24/7 on-call coverage required