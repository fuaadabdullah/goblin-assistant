# Attestation Webhook Security Audit

## Critical Findings

### 1. **CRITICAL: `/attest-node` Endpoint is Completely Unauthenticated**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L193-L207)

**Issue:** Any client can POST to `/attest-node` and attest arbitrary nodes without authentication.

```python
@app.post("/attest-node")
async def attest_node(request: Request):
    """Manually attest a node (for testing/admin purposes)"""
    try:
        data = await request.json()
        node_id = data.get('node_id')
        # ❌ NO AUTH CHECK
```

**Threat:** Attacker can attest compromised nodes, bypassing entire hardware attestation scheme.

**Severity:** 🔴 CRITICAL (Breaks security model)

---

### 2. **CRITICAL: `/validate` Webhook Endpoint Missing mTLS Verification**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L59-L91)

**Issue:** Kubernetes sends admission webhook calls with mTLS client certificate, but code doesn't validate the certificate or request signature.

```python
@app.post("/validate")
async def validate_admission(request: Request):
    """Admission controller webhook endpoint"""
    try:
        body = await request.json()
        # ❌ NO CERTIFICATE VERIFICATION
        # ❌ NO REQUEST SIGNATURE CHECK
```

**Threat:** Attacker can spoof API server and inject false AdmissionReview requests.

**Severity:** 🔴 CRITICAL (Breaks admission webhook security model)

---

### 3. **HIGH: `/attestation-status` Endpoint Exposes All Node Status**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L178-L184)

**Issue:** Unauthenticated endpoint returns list of all attested nodes.

```python
@app.get("/attestation-status")
async def get_attestation_status():
    """Get current attestation status for all nodes"""
    try:
        attested_nodes = attestation_service.list_attested_nodes()
        # ❌ NO AUTH CHECK
        return {
            "attested_nodes": attested_nodes,  # ← Publicly visible
```

**Threat:** Reconnaissance - attacker learns which nodes are attested vs. revoked.

**Severity:** 🟠 HIGH (Information disclosure)

---

### 4. **HIGH: Error Responses Leak Internal Details**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L97-L112)

**Issue:** Errors return full exception messages and status 500, exposing internal state.

```python
    except Exception as e:
        error_msg = f'Attestation validation error: {str(e)}'
        # ← Leaks exception type and details
```

**Threat:** Attacker learns about validation logic, Redis errors, etc.

**Severity:** 🟠 HIGH (Information disclosure)

---

### 5. **MEDIUM: No Audit Logging of Requests**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L59-L112)

**Issue:** No log of:
- Who (client cert CN) called the endpoint
- What was validated
- Whether admission was denied
- Timestamp, request hash, etc.

**Threat:** No incident response trail; cannot prove if webhook was compromised.

**Severity:** 🟡 MEDIUM (Compliance/observability)

---

### 6. **MEDIUM: Import Broken After Service Refactor**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L11)

**Issue:** Still uses old module-level singleton import:

```python
from .attestation_service import attestation_service  # ← DOESN'T EXIST ANYMORE
```

But `attestation_service.py` now uses factory pattern:
- `get_attestation_service()` (lazy init)
- `reset_attestation_service()` (for testing)
- No module-level `attestation_service` instance

**Threat:** Code will crash on import with `ImportError`.

**Severity:** 🟡 MEDIUM (Runtime breakage)

---

### 7. **LOW: No Rate Limiting**
**Location:** [attestation_webhook.py](api/attestation_webhook.py#L193-L207)

**Issue:** `/attest-node` has no rate limiting.

**Threat:** DoS via repeated attestation calls.

**Severity:** 🔵 LOW (Mitigated by infrastructure, but good to have)

---

## Remediation Plan

### Phase 1: Fix Runtime Breakage (BLOCKING)
- [ ] Update import to use factory: `from .attestation_service import get_attestation_service`
- [ ] Update all `attestation_service.xxx()` calls to `get_attestation_service().xxx()`
- [ ] Add comprehensive logging

### Phase 2: Secure `/validate` Webhook (CRITICAL)
- [ ] Extract client certificate from mTLS connection
- [ ] Validate certificate is signed by Kubernetes API server CA
- [ ] Log certificate CN (who called the webhook)
- [ ] Validate request UID is present and non-empty
- [ ] Return generic error messages (don't leak internals)

### Phase 3: Secure `/attest-node` (CRITICAL)
- [ ] Require Bearer token (Kubernetes service account)
- [ ] Validate token has `sandbox:attestation:write` permission
- [ ] Log all attest attempts (success/failure, who, when)
- [ ] Add rate limiting (e.g., 10 requests/min per service account)
- [ ] Return 401/403 for unauthorized requests

### Phase 4: Secure `/attestation-status` (HIGH)
- [ ] Require service account token
- [ ] Add rate limiting
- [ ] Log access requests

---

## Environment Requirements

For mTLS on `/validate`:
- Service must be deployed with mTLS cert (from cert-manager or manual)
- Kubernetes will verify client cert automatically (mTLS in reverse)
- Code must extract cert from `request.client` or headers

For Bearer token on `/attest-node`:
- Service account token from `Authorization: Bearer <token>` header
- Use Kubernetes client lib to validate token
- Optional: Use webhook token review API for validation

---

## Success Criteria

✅ All endpoints require appropriate authentication  
✅ Error messages are generic (no internal detail leaks)  
✅ All requests logged with audit trail (who, when, what, result)  
✅ `/attest-node` restricted to authorized service accounts  
✅ `/validate` validates mTLS certificate origin  
✅ Rate limiting prevents abuse  
✅ Code no longer crashes on import  
