# Attestation Webhook Production Deployment Guide

## Overview
This guide covers the production deployment of the hardened attestation validation webhook with mTLS, TokenReview-based service account authentication, and Redis-backed rate limiting.

**Status**: Ready for production deployment
- ✅ Core authentication: TokenReview-based SA validation
- ✅ Rate limiting: Redis-backed fixed-window limiter
- ✅ mTLS: Proxy-header-based client certificate verification
- ✅ Unit tests: 100% pass rate with mocked Kubernetes and Redis
- ✅ Exception handling: Narrowed to specific types (no broad `except Exception`)
- ✅ Type hints: Complete for decorators and critical functions

---

## Pre-Deployment Checklist

### 1. Code Verification
- [ ] All tests pass: `cd api && pytest tests/test_attestation_webhook.py -v`
- [ ] Lint/type checks clean: Static analysis warnings addressed
- [ ] Redis client annotation in place: `attestation_service.py` line 417
- [ ] Exception handling narrowed: No unintentional broad excepts

### 2. Environment Prerequisites
- [ ] cert-manager v1.14+ installed and running in the cluster
- [ ] Production CA certificate and private key available (or use Let's Encrypt)
- [ ] Redis service deployed and accessible at configured URL
- [ ] RBAC permissions verified for webhook service account
- [ ] Attestation service configuration validated (TPM/GCP/AWS PCR values set)

### 3. Network & Security
- [ ] NetworkPolicy rules configured to allow API server to reach webhook on port 8443
- [ ] Pod security standards enforced (pod-security.kubernetes.io labels)
- [ ] Network policies restrict egress to DNS and Redis only
- [ ] Webhook Pod runs non-root (runAsUser: 1000) with minimal capabilities

---

## Production Deployment Steps

### Phase 1: Certificate Management Setup

#### Option A: Use Existing Self-Signed Issuer (for initial testing)
The cluster likely already has a `sandbox-issuer` configured. Verify:

```bash
kubectl get issuer -n sandbox
# Expected output:
# NAME             READY   AGE
# sandbox-issuer   True    1d
```

#### Option B: Configure Production CA (Recommended)
Create a production-grade issuer backed by your organization's CA or Let's Encrypt:

```yaml
# Example: Let's Encrypt (ACME) Issuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: production-ca
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: security-team@your-org.com
    privateKeySecretRef:
      name: production-ca-key
    solvers:
    - http01:
        ingress: {}

---
# Or: CA Certificate Issuer (for internal PKI)
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: internal-ca
  namespace: sandbox
spec:
  ca:
    secretName: internal-ca-certs  # Secret containing ca.crt and ca.key
```

Then apply:

```bash
kubectl apply -f issuer-config.yaml
```

### Phase 2: Certificate Creation & Secret Management

#### Ensure Certificate Resource Exists

```bash
kubectl get certificate -n sandbox attestation-webhook-cert
```

If not present, create:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: attestation-webhook-cert
  namespace: sandbox
spec:
  secretName: attestation-webhook-cert
  issuerRef:
    name: production-ca  # Or sandbox-issuer for testing
    kind: Issuer
  dnsNames:
  - attestation-webhook.sandbox.svc
  - attestation-webhook.sandbox.svc.cluster.local
  usages:
  - digital signature
  - key encipherment
  - server auth
```

Verify secret creation (cert-manager will populate `tls.crt` and `tls.key`):

```bash
kubectl describe certificate -n sandbox attestation-webhook-cert
# Should show: Status.Conditions: Ready=True

# Verify secret:
kubectl get secret -n sandbox attestation-webhook-cert -o yaml
# Must contain:
#   tls.crt: <base64-encoded certificate>
#   tls.key: <base64-encoded private key>
#   ca.crt: <base64-encoded CA certificate>
```

### Phase 3: Populate ValidatingWebhookConfiguration with caBundle

The `caBundle` field must contain the base64-encoded CA certificate so the Kubernetes API server can verify the webhook's certificate during mTLS handshake.

#### Automatic Update (via cert-manager annotation)
Add cert-manager annotation to auto-sync the caBundle:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: sandbox-attestation-webhook
  annotations:
    cert-manager.io/inject-ca-from: sandbox/attestation-webhook-cert  # Auto-sync caBundle
  labels:
    app: attestation-webhook
webhooks:
- name: attestation-validator.sandbox.svc.cluster.local
  # ... rest of config remains the same
  clientConfig:
    service:
      name: attestation-webhook
      namespace: sandbox
      path: "/validate"
      port: 443
    caBundle: ""  # cert-manager will populate this automatically
```

Apply the updated config:

```bash
kubectl apply -f k8s/attestation-webhook.yaml
```

Verify caBundle population (may take 5-10 seconds):

```bash
kubectl get validatingwebhookconfigurations sandbox-attestation-webhook -o yaml | grep -A 5 caBundle
# Should show: caBundle: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0t... (base64 data)
```

#### Manual Update (if cert-manager annotation not working)
Extract and manually populate caBundle:

```bash
# Extract CA certificate from secret
CA_CERT=$(kubectl get secret -n sandbox attestation-webhook-cert -o jsonpath='{.data.ca\.crt}')

# Update ValidatingWebhookConfiguration
kubectl patch validatingwebhookconfigurations sandbox-attestation-webhook \
  --type merge -p "{\"webhooks\":[{\"name\":\"attestation-validator.sandbox.svc.cluster.local\",\"clientConfig\":{\"caBundle\":\"$CA_CERT\"}}]}"
```

### Phase 4: Deploy Webhook

Ensure the Deployment uses the SSL certificates:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: attestation-webhook
  namespace: sandbox
spec:
  replicas: 2  # HA setup
  selector:
    matchLabels:
      app: attestation-webhook
  template:
    metadata:
      labels:
        app: attestation-webhook
    spec:
      serviceAccountName: sandbox-webhook-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000

      containers:
      - name: webhook
        image: goblin-assistant:latest  # Must be tagged with production release
        command:
        - python
        - -m
        - uvicorn
        - api.attestation_webhook:app
        - --host
        - "0.0.0.0"
        - --port
        - "8443"
        - --ssl-keyfile
        - /etc/webhook/certs/tls.key
        - --ssl-certfile
        - /etc/webhook/certs/tls.crt
        - --workers
        - "2"  # Multiple workers for production
        
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: LOG_LEVEL
          value: "INFO"  # Change to DEBUG for troubleshooting
        
        volumeMounts:
        - name: webhook-certs
          mountPath: /etc/webhook/certs
          readOnly: true
        
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8443
            scheme: HTTPS
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: 8443
            scheme: HTTPS
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3

      volumes:
      - name: webhook-certs
        secret:
          secretName: attestation-webhook-cert
```

Deploy:

```bash
kubectl apply -f k8s/attestation-webhook.yaml
```

### Phase 5: Canary Rollout & Verification

#### Step 1: Verify Webhook Readiness

```bash
# Check pod status
kubectl get pods -n sandbox -l app=attestation-webhook
# Wait for all replicas to be Ready

# Check webhook logs
kubectl logs -n sandbox -l app=attestation-webhook -f --tail=50
# Should show: "Uvicorn running on https://0.0.0.0:8443"
```

#### Step 2: Test with Non-Critical Namespace First

Create a test Pod in a namespace NOT protected by the webhook:

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  namespace: default
spec:
  containers:
  - name: test
    image: alpine:latest
    command: ["sleep", "3600"]
EOF

# Pod should be created without webhook interference (no label selector match)
kubectl get pod -n default test-pod
```

#### Step 3: Test Webhook Functionality

Create a Pod in the webhook-protected `sandbox` namespace:

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: attestation-test-pod
  namespace: sandbox
  labels:
    app: goblin-assistant-worker
spec:
  containers:
  - name: test
    image: alpine:latest
    command: ["sleep", "3600"]
EOF

# Check webhook logs for validation attempt
kubectl logs -n sandbox -l app=attestation-webhook -f --tail=20 | grep attestation_review_received
```

#### Step 4: Audit Log Verification

Check Kubernetes audit logs to confirm webhook is invoked:

```bash
# On the control plane node or via logs aggregator
grep "attestation-webhook" /var/log/kubernetes/audit.log | head -5
# Should show successful webhook calls

# Or if using structured logging:
kubectl logs -n kube-system -l component=kube-apiserver | grep attestation-webhook
```

#### Step 5: Monitor Rate Limiting

Test that rate limiting is enforced (optional):

```bash
# Simulate rapid attestation requests
for i in {1..10}; do
  kubectl apply -f test-pod.yaml &
done
wait

# Check logs for rate limit warnings
kubectl logs -n sandbox -l app=attestation-webhook | grep rate_limit_exceeded
```

---

## Post-Deployment Validation

### 1. Verify mTLS Handshake
Confirm that the Kubernetes API server successfully verifies the webhook's certificate:

```bash
# On a node with access to control plane:
openssl s_client -connect attestation-webhook.sandbox.svc.cluster.local:443 \
  -CAfile /path/to/ca.crt -showcerts

# Should show: "Verify return code: 0 (ok)"
```

### 2. Verify TokenReview Authentication
Check that service account tokens are properly validated:

```bash
# Look for successful token review logs
kubectl logs -n sandbox -l app=attestation-webhook | grep "token_review_success\|token_review_api_exception"

# Should show successful reviews for SA requests
```

### 3. Monitor Metrics (if Prometheus enabled)
Set up alerts for:
- High rate limit hits: `rate_limit_exceeded` (should be rare in steady state)
- Webhook latency: Response time for `/validate` endpoint (should be < 100ms)
- Admission denials: Track denied Pods for security analysis

```yaml
# Example Prometheus alert
groups:
- name: attestation-webhook
  rules:
  - alert: HighAdmissionDenialRate
    expr: increase(admission_denied_total[5m]) > 10
    annotations:
      summary: "Unusual number of Pods denied by attestation webhook"
```

### 4. Test Failure Modes
Verify the `failurePolicy: Fail` behavior by temporarily disabling the webhook:

```bash
# Scale webhook to 0 replicas
kubectl scale deployment -n sandbox attestation-webhook --replicas=0

# Try to create a Pod (should be denied because webhook is unavailable)
# The failurePolicy=Fail means: if webhook unreachable, deny the request
kubectl apply -f test-pod.yaml

# Should see: "error from server (InternalError): error when creating..."

# Restore webhook
kubectl scale deployment -n sandbox attestation-webhook --replicas=2
```

---

## Rollback Procedures

If issues arise after deployment:

### Option 1: Scale Down Webhook (Temporary)
```bash
kubectl scale deployment -n sandbox attestation-webhook --replicas=0
# Pods will be admitted (failurePolicy=Fail means deny, but with 0 replicas = unavailable = deny)
# This is a safety circuit breaker; use only in emergency
```

### Option 2: Remove Webhook Configuration (Immediate)
```bash
kubectl delete validatingwebhookconfigurations sandbox-attestation-webhook
# Immediately restores Pod admission without webhook validation
# Note: Already-denied Pods require manual eviction/recreation
```

### Option 3: Revert to Previous Webhook Version
```bash
kubectl set image deployment/attestation-webhook -n sandbox \
  webhook=goblin-assistant:previous-tag --record
```

---

## Security Hardening Checklist

- [ ] **mTLS Verification**: API server successfully performs TLS handshake with webhook
- [ ] **caBundle Populated**: ValidatingWebhookConfiguration contains base64-encoded CA cert
- [ ] **Service Account Validation**: TokenReview API is used to validate service account tokens
- [ ] **Rate Limiting**: Redis-backed limiter enforces per-SA rate limits
- [ ] **Exception Handling**: All exceptions narrowed to specific types (no broad catches)
- [ ] **Pod Security**: Running non-root (1000:1000), read-only filesystem, minimal capabilities
- [ ] **Network Policies**: Webhook pod can only reach DNS and Redis (no outbound internet)
- [ ] **Audit Logging**: All admission decisions logged with UIDs and Pod metadata
- [ ] **Monitoring**: Alerts configured for high denial rates and webhook unavailability

---

## Troubleshooting

### Webhook Not Invoked
```bash
# Verify ValidatingWebhookConfiguration is registered
kubectl get validatingwebhookconfigurations
kubectl describe validatingwebhookconfigurations sandbox-attestation-webhook

# Check Pod labels match objectSelector
kubectl get pod -n sandbox -o jsonpath='{.items[*].metadata.labels}' | grep app=goblin-assistant-worker

# Check namespace labels match namespaceSelector
kubectl get ns sandbox -o yaml | grep -A 2 labels
```

### mTLS Handshake Failures
```bash
# Check certificate validity
kubectl get certificate -n sandbox attestation-webhook-cert -o yaml | grep -A 5 status

# Verify secret has both tls.crt and tls.key
kubectl get secret -n sandbox attestation-webhook-cert -o yaml | grep -E "tls\.(crt|key)"

# Check webhook logs for TLS errors
kubectl logs -n sandbox -l app=attestation-webhook | grep -i "ssl\|tls\|certificate"
```

### High Denial Rate
```bash
# Check service account permissions
kubectl get rolebindings -n sandbox -l app=attestation-webhook

# Verify TokenReview works
kubectl create token system:serviceaccount:sandbox:sandbox-webhook-sa

# Check rate limiting configuration
kubectl get configmap -n sandbox | grep attestation
```

---

## Monitoring & Alerting

Recommended metrics to track in production:

1. **Webhook Availability**: Pod replicas running / desired
2. **Admission Decisions**: Allowed vs. Denied (by namespace, reason)
3. **Rate Limit Events**: Hits per SA per minute
4. **Latency**: P50, P95, P99 response times for `/validate`
5. **Error Rate**: TokenReview failures, Redis errors
6. **Certificate Expiry**: Days until attestation-webhook-cert expires

Set up alerts:
- Webhook unavailable for > 1 minute → Page on-call
- Certificate expires in < 7 days → Create ticket
- Rate limit hits > 5 per minute → Investigate malicious traffic

---

## References

- [Kubernetes Admission Webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [TokenReview API](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.28/#tokenreview-v1-authentication-k8s-io)
- [ValidatingWebhookConfiguration](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.28/#validatingwebhookconfiguration-v1-admissionregistration-k8s-io)
