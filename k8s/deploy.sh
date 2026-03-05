#!/bin/bash

# Sandbox Kubernetes Deployment Script
# Deploys the goblin-assistant sandbox with production-grade security

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="sandbox"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Unable to connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Dependencies check passed"
}

create_namespace() {
    log_info "Creating namespace with Pod Security Standards..."

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace '$NAMESPACE' already exists"
        read -p "Continue with existing namespace? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    else
        kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
        log_success "Namespace created with Pod Security Standards enforced"
    fi
}

deploy_rbac() {
    log_info "Deploying RBAC (Service Accounts and Roles)..."
    kubectl apply -f "$SCRIPT_DIR/rbac.yaml"
    log_success "RBAC deployed"
}

deploy_secrets() {
    log_info "Checking secrets..."

    if ! kubectl get secret sandbox-secrets -n "$NAMESPACE" &> /dev/null; then
        log_warning "sandbox-secrets not found. Creating with default values..."
        log_warning "⚠️  CHANGE THESE DEFAULTS IN PRODUCTION! ⚠️"
        kubectl apply -f "$SCRIPT_DIR/secrets.yaml"
        log_warning "Default secrets deployed - update immediately in production!"
    else
        log_info "Secrets already exist"
    fi

    # Check for cosign key
    if ! kubectl get secret cosign-public-key -n "$NAMESPACE" &> /dev/null; then
        log_warning "cosign-public-key not found - image verification disabled"
    else
        log_success "cosign public key configured"
    fi
}

deploy_infrastructure() {
    log_info "Deploying infrastructure (Redis, MinIO)..."
    kubectl apply -f "$SCRIPT_DIR/services.yaml"

    log_info "Waiting for infrastructure to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n "$NAMESPACE"
    kubectl wait --for=condition=available --timeout=300s deployment/minio -n "$NAMESPACE"

    log_success "Infrastructure deployed and ready"
}

deploy_applications() {
    log_info "Deploying applications..."
    kubectl apply -f "$SCRIPT_DIR/deployment-api.yaml"
    kubectl apply -f "$SCRIPT_DIR/deployment-worker.yaml"

    log_info "Waiting for applications to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/goblin-assistant-api -n "$NAMESPACE"
    kubectl wait --for=condition=available --timeout=300s deployment/goblin-assistant-worker -n "$NAMESPACE"

    log_success "Applications deployed and ready"
}

deploy_networking() {
    log_info "Configuring network policies..."
    kubectl apply -f "$SCRIPT_DIR/network-policy.yaml"
    log_success "Network policies configured (default deny enforced)"
}

deploy_scaling() {
    log_info "Setting up scaling and monitoring..."
    kubectl apply -f "$SCRIPT_DIR/scaling.yaml"
    log_success "Scaling and monitoring configured"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Check pod status
    local total_pods
    total_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l)
    local running_pods
    running_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | grep Running | wc -l)

    if [ "$running_pods" -eq "$total_pods" ]; then
        log_success "All pods are running ($running_pods/$total_pods)"
    else
        log_warning "Some pods are not running ($running_pods/$total_pods total)"
        kubectl get pods -n "$NAMESPACE"
    fi

    # Check services
    local services
    services=$(kubectl get services -n "$NAMESPACE" --no-headers | wc -l)
    log_info "Services deployed: $services"

    # Check security
    log_info "Security verification:"
    kubectl get networkpolicy -n "$NAMESPACE"
    kubectl get role,rolebinding -n "$NAMESPACE"

    # Test API health
    local api_pod
    api_pod=$(kubectl get pods -n "$NAMESPACE" -l app=goblin-assistant-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "$api_pod" ]; then
        log_info "Testing API health endpoint..."
        if kubectl exec -n "$NAMESPACE" "$api_pod" -- curl -f http://localhost:8001/health &> /dev/null; then
            log_success "API health check passed"
        else
            log_warning "API health check failed"
        fi

        log_info "Testing metrics endpoint..."
        if kubectl exec -n "$NAMESPACE" "$api_pod" -- curl -f http://localhost:8001/sandbox/metrics &> /dev/null; then
            log_success "Metrics endpoint accessible"
        else
            log_warning "Metrics endpoint not accessible"
        fi
    fi
}

show_summary() {
    log_success "🎉 Sandbox deployment completed!"
    echo
    echo "📋 Deployment Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Namespace: $NAMESPACE"
    echo "API Endpoint: $(kubectl get svc goblin-assistant-api -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}:{.spec.ports[0].port}' 2>/dev/null || echo 'N/A')"
    echo "MinIO Console: http://$(kubectl get svc minio-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo 'N/A'):9001"
    echo
    echo "🔒 Security Features Enabled:"
    echo "  ✅ Pod Security Standards (Restricted)"
    echo "  ✅ Network Policies (Default Deny)"
    echo "  ✅ RBAC with minimal permissions"
    echo "  ✅ Non-root container execution"
    echo "  ✅ No privilege escalation"
    echo
    echo "📊 Monitoring:"
    echo "  ✅ Prometheus metrics at /sandbox/metrics"
    echo "  ✅ Alerting rules configured"
    echo "  ✅ Grafana dashboard available"
    echo
    echo "🚨 IMPORTANT PRODUCTION STEPS:"
    echo "  1. Change default secrets (API key, S3 credentials)"
    echo "  2. Configure TLS certificates"
    echo "  3. Set up ingress with proper authentication"
    echo "  4. Configure log aggregation and monitoring"
    echo "  5. Set up backup strategy for Redis/MinIO"
    echo
    echo "📖 See k8s/README.md for detailed documentation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main deployment function
main() {
    echo "🐳 Goblin Assistant Sandbox - Kubernetes Deployment"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo

    check_dependencies
    create_namespace
    deploy_rbac
    deploy_secrets
    deploy_infrastructure
    deploy_applications
    deploy_networking
    deploy_scaling
    verify_deployment
    show_summary

    log_success "Deployment script completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    "check")
        check_dependencies
        ;;
    "cleanup")
        log_warning "Cleaning up sandbox deployment..."
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        log_success "Cleanup completed"
        ;;
    "status")
        log_info "Deployment status:"
        kubectl get all -n "$NAMESPACE"
        ;;
    *)
        main
        ;;
esac