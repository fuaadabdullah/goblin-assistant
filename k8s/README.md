# Sandbox Kubernetes Deployment

This directory contains the complete Kubernetes manifests for deploying the goblin-assistant sandbox with production-grade security and monitoring.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Service   │    │  Worker Service │    │  Redis/MinIO    │
│                 │    │                 │    │                 │
│ • REST API      │    │ • RQ Workers    │    │ • Job Queue     │
│ • Metrics       │    │ • Docker Exec   │    │ • Artifact Store │
│ • Rate Limiting │    │ • Security      │    │ • Metadata       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                        Network Policies (Default Deny)
```

## Security Features

### Pod Security Standards (MANDATORY)
- **Restricted** PodSecurity Standard enforced at namespace level
- Non-root user execution (UID 1000)
- No privilege escalation
- Read-only root filesystem (API pods)
- Dropped capabilities (ALL)

### Network Security
- **Default deny** all ingress/egress traffic
- Explicit allow rules for required communication
- No host network access
- DNS and HTTPS egress only (API pods)

### RBAC
- Minimal service account permissions
- Secret access restricted to specific keys
- Docker socket access limited to worker pods

## Deployment Order

Deploy in this exact order to ensure dependencies:

```bash
# 1. Create namespace with security standards
kubectl apply -f namespace.yaml

# 2. Create RBAC (service accounts and roles)
kubectl apply -f rbac.yaml

# 3. Create secrets (change defaults in production!)
kubectl apply -f secrets.yaml

# 4. Deploy infrastructure (Redis, MinIO)
kubectl apply -f services.yaml

# 5. Deploy applications
kubectl apply -f deployment-api.yaml
kubectl apply -f deployment-worker.yaml

# 6. Configure networking
kubectl apply -f network-policy.yaml

# 7. Set up scaling and monitoring
kubectl apply -f scaling.yaml
```

## Configuration

### Secrets (CHANGE THESE IN PRODUCTION!)

```bash
# Update API key
kubectl create secret generic sandbox-secrets \
  --from-literal=api-key='your-secure-api-key' \
  --from-literal=s3-access-key='your-minio-user' \
  --from-literal=s3-secret-key='your-minio-password' \
  --dry-run=client -o yaml | kubectl apply -f -

# Add cosign public key for image verification (optional)
kubectl create secret generic cosign-public-key \
  --from-file=pubkey.pem=/path/to/cosign.pub \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Environment Variables

Key configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTIFACT_TTL_DAYS` | 7 | Artifact retention period |
| `MAX_ARTIFACT_SIZE_MB` | 10 | Maximum artifact size |
| `JOB_TIMEOUT_SECONDS` | 300 | Maximum job execution time |
| `ARTIFACT_CLEANUP_INTERVAL_HOURS` | 24 | Cleanup frequency |

## Monitoring

### Prometheus Metrics

The sandbox exposes comprehensive metrics at `/sandbox/metrics`:

- `sandbox_jobs_submitted_total` - Job submission counter
- `sandbox_jobs_running` - Active job gauge
- `sandbox_job_duration_seconds` - Execution time histogram
- `sandbox_job_failures_total` - Failure tracking
- `sandbox_container_kills_total` - Container termination tracking
- `sandbox_queue_depth` - Queue monitoring

### Grafana Dashboard

Import `grafana-dashboard.json` for a complete monitoring dashboard featuring:

- Real-time job success rates and queue depths
- Performance metrics (P50/P95 latency)
- Failure analysis and alerting
- SLO tracking (7-day availability and latency)
- Artifact storage monitoring

### Alerting Rules

Critical alerts configured in `prometheus_rules.yml`:

- Job failure rate >5% over 5 minutes
- Queue depth >50 jobs
- Job duration P95 >270 seconds
- Container kills >5 per 10 minutes
- SLO breaches (95% availability, 120s P95)

## Scaling

### Horizontal Pod Autoscaler

Workers automatically scale based on queue depth:

```yaml
minReplicas: 1
maxReplicas: 5
targetQueueDepth: 10  # Scale up when queue > 10
```

### Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| API | 100m | 500m | 128Mi | 512Mi |
| Worker | 200m | 1000m | 256Mi | 1Gi |
| Redis | 50m | 100m | 64Mi | 128Mi |
| MinIO | 100m | 200m | 128Mi | 256Mi |

## Security Hardening Checklist

### Pre-Deployment
- [ ] Change default API key and S3 credentials
- [ ] Configure cosign public key for image verification
- [ ] Set up TLS certificates for MinIO
- [ ] Review and customize resource limits
- [ ] Configure external DNS for ingress

### Runtime Security
- [ ] Enable audit logging
- [ ] Set up log aggregation (ELK/EFK)
- [ ] Configure backup strategy for Redis/MinIO
- [ ] Set up monitoring alerts
- [ ] Test pod security policies

### Network Security
- [ ] Configure ingress controller with TLS
- [ ] Set up network policies for external access
- [ ] Enable service mesh (Istio/Linkerd) if needed
- [ ] Configure rate limiting at ingress level

## Troubleshooting

### Common Issues

**Pods stuck in Pending:**
```bash
kubectl describe pod <pod-name>
# Check resource requests, node selectors, taints/tolerations
```

**Image verification failures:**
```bash
# Check cosign secret
kubectl get secret cosign-public-key -o yaml

# Verify image signature manually
cosign verify --key cosign.pub goblin-assistant-sandbox:latest
```

**Network connectivity issues:**
```bash
# Check network policies
kubectl get networkpolicy -n sandbox

# Test pod-to-pod communication
kubectl exec -it <pod> -- curl <service>
```

**Metrics not appearing:**
```bash
# Check Prometheus ServiceMonitor
kubectl get servicemonitor -n sandbox

# Verify metrics endpoint
kubectl exec -it <api-pod> -- curl localhost:8001/sandbox/metrics
```

## Backup and Recovery

### Redis Backup
```bash
# Enable AOF persistence (already configured)
kubectl exec redis-pod -- redis-cli save

# Copy backup
kubectl cp redis-pod:/data/appendonly.aof ./redis-backup.aof
```

### MinIO Backup
```bash
# Use mc (MinIO client) for backups
mc mirror minio-service/goblin-sandbox ./backup/
```

### Recovery
1. Restore Redis data to new pod
2. Restore MinIO bucket data
3. Update any persistent job references
4. Verify application functionality

## Production Considerations

### High Availability
- Deploy across multiple availability zones
- Configure pod anti-affinity
- Set up proper PDBs (already included)
- Consider stateful sets for Redis/MinIO in large deployments

### Performance Tuning
- Adjust resource limits based on load testing
- Configure Redis persistence and replication
- Set up MinIO distributed mode for large-scale storage
- Tune Prometheus scrape intervals based on cluster size

### Compliance
- Enable audit logging at Kubernetes level
- Configure log retention policies
- Set up compliance monitoring (CIS benchmarks)
- Regular security scans and updates

## Support

For issues with this deployment:

1. Check the troubleshooting section above
2. Review Kubernetes and application logs
3. Verify configuration against security requirements
4. Contact the platform team for assistance

---

**Security Notice:** This deployment implements production-grade security controls. Review and test thoroughly before deploying to production environments.