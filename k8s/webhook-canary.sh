#!/bin/bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-sandbox}"
CONTROL_NAMESPACE="${CONTROL_NAMESPACE:-default}"
WEBHOOK_LABEL_KEY="${WEBHOOK_LABEL_KEY:-app}"
WEBHOOK_LABEL_VALUE="${WEBHOOK_LABEL_VALUE:-goblin-assistant-worker}"
WEBHOOK_DEPLOYMENT="${WEBHOOK_DEPLOYMENT:-attestation-webhook}"
WEBHOOK_CONFIG="${WEBHOOK_CONFIG:-sandbox-attestation-webhook}"
RUN_ID="$(date +%s)"
CONTROL_POD="webhook-control-test-${RUN_ID}"
CANARY_POD="webhook-canary-test-${RUN_ID}"

info() { echo "[INFO] $*"; }
success() { echo "[SUCCESS] $*"; }
warn() { echo "[WARN] $*"; }

cleanup() {
  kubectl delete pod "$CONTROL_POD" -n "$CONTROL_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
  kubectl delete pod "$CANARY_POD" -n "$NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
}
trap cleanup EXIT

info "Checking kubectl connectivity"
if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "[ERROR] Unable to reach Kubernetes API server"
  exit 1
fi

info "Checking webhook deployment readiness"
kubectl rollout status deployment/"$WEBHOOK_DEPLOYMENT" -n "$NAMESPACE" --timeout=180s

info "Checking ValidatingWebhookConfiguration caBundle"
CA_BUNDLE_LEN=$(kubectl get validatingwebhookconfiguration "$WEBHOOK_CONFIG" -o jsonpath='{.webhooks[0].clientConfig.caBundle}' | wc -c)
if [[ "$CA_BUNDLE_LEN" -le 0 ]]; then
  warn "caBundle is empty. cert-manager injection may not be complete."
else
  success "caBundle length: $CA_BUNDLE_LEN"
fi

info "Creating control pod in $CONTROL_NAMESPACE (outside webhook selector scope)"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: ${CONTROL_POD}
  namespace: ${CONTROL_NAMESPACE}
spec:
  containers:
  - name: test
    image: alpine:3.20
    command: ["sh", "-c", "sleep 300"]
EOF

kubectl wait --for=condition=Ready pod/"$CONTROL_POD" -n "$CONTROL_NAMESPACE" --timeout=120s
success "Control pod admitted and ready"

info "Creating canary pod in $NAMESPACE with selector label ${WEBHOOK_LABEL_KEY}=${WEBHOOK_LABEL_VALUE}"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: ${CANARY_POD}
  namespace: ${NAMESPACE}
  labels:
    ${WEBHOOK_LABEL_KEY}: ${WEBHOOK_LABEL_VALUE}
spec:
  containers:
  - name: test
    image: alpine:3.20
    command: ["sh", "-c", "sleep 300"]
EOF

set +e
kubectl wait --for=condition=Ready pod/"$CANARY_POD" -n "$NAMESPACE" --timeout=120s
CANARY_WAIT_EXIT=$?
set -e

if [[ "$CANARY_WAIT_EXIT" -eq 0 ]]; then
  success "Canary pod admitted and ready"
else
  warn "Canary pod did not become ready in time. Capturing diagnostics..."
fi

info "Recent canary pod events"
kubectl describe pod "$CANARY_POD" -n "$NAMESPACE" || true

info "Recent webhook logs"
kubectl logs -n "$NAMESPACE" -l app=attestation-webhook --tail=200 || true

info "Recent namespace events"
kubectl get events -n "$NAMESPACE" --sort-by=.lastTimestamp | tail -n 30 || true

success "Canary verification completed"
