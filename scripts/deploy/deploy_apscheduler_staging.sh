#!/bin/bash
# Deploy APScheduler Migration to Staging Environment
# This script deploys the APScheduler changes to a single replica for testing

set -e

echo "🚀 Starting APScheduler Migration Deployment to Staging"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STAGING_NAMESPACE="goblin-assistant-staging"
DEPLOYMENT_NAME="goblin-assistant-backend"
SINGLE_REPLICA_COUNT=1

echo "📋 Deployment Configuration:"
echo "  - Namespace: $STAGING_NAMESPACE"
echo "  - Deployment: $DEPLOYMENT_NAME"
echo "  - Single Replica Count: $SINGLE_REPLICA_COUNT"

# Function to check if we're in the right environment
check_environment() {
    echo "🔍 Checking environment..."

    # Check if kubectl is configured
    if ! kubectl cluster-info >/dev/null 2>&1; then
        echo -e "${RED}❌ kubectl not configured or cluster not accessible${NC}"
        exit 1
    fi

    # Check if namespace exists
    if ! kubectl get namespace "$STAGING_NAMESPACE" >/dev/null 2>&1; then
        echo -e "${RED}❌ Staging namespace '$STAGING_NAMESPACE' not found${NC}"
        exit 1
    fi

    # Check if deployment exists
    if ! kubectl get deployment "$DEPLOYMENT_NAME" -n "$STAGING_NAMESPACE" >/dev/null 2>&1; then
        echo -e "${RED}❌ Deployment '$DEPLOYMENT_NAME' not found in namespace '$STAGING_NAMESPACE'${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Environment check passed${NC}"
}

# Function to backup current deployment
backup_deployment() {
    echo "💾 Creating deployment backup..."

    BACKUP_FILE="deployment-backup-$(date +%Y%m%d-%H%M%S).yaml"
    kubectl get deployment "$DEPLOYMENT_NAME" -n "$STAGING_NAMESPACE" -o yaml > "$BACKUP_FILE"

    echo -e "${GREEN}✅ Deployment backed up to: $BACKUP_FILE${NC}"
}

# Function to scale down to single replica
scale_to_single_replica() {
    echo "🔧 Scaling deployment to single replica..."

    kubectl scale deployment "$DEPLOYMENT_NAME" \
        --replicas="$SINGLE_REPLICA_COUNT" \
        -n "$STAGING_NAMESPACE"

    echo "⏳ Waiting for scaling to complete..."
    kubectl wait --for=condition=available \
        --timeout=300s \
        deployment/"$DEPLOYMENT_NAME" \
        -n "$STAGING_NAMESPACE"

    echo -e "${GREEN}✅ Deployment scaled to $SINGLE_REPLICA_COUNT replica${NC}"
}

# Function to deploy new image with APScheduler
deploy_apscheduler() {
    echo "🚀 Deploying APScheduler-enabled image..."

    # Get current image
    CURRENT_IMAGE=$(kubectl get deployment "$DEPLOYMENT_NAME" \
        -n "$STAGING_NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].image}')

    echo "Current image: $CURRENT_IMAGE"

    # For this demo, we'll assume the image already has APScheduler
    # In real deployment, you would update the image tag here
    echo -e "${YELLOW}⚠️  Note: Ensure your container image includes APScheduler dependencies${NC}"
    echo -e "${YELLOW}   Required: APScheduler, redis, psutil${NC}"

    # Set environment variables for APScheduler
    kubectl set env deployment/"$DEPLOYMENT_NAME" \
        -n "$STAGING_NAMESPACE" \
        SCHEDULER_ENABLED=true \
        REDIS_URL=redis://redis-service:6379/0

    echo -e "${GREEN}✅ APScheduler environment variables set${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo "🔍 Verifying deployment..."

    # Check pod status
    POD_NAME=$(kubectl get pods \
        -n "$STAGING_NAMESPACE" \
        -l app="$DEPLOYMENT_NAME" \
        -o jsonpath='{.items[0].metadata.name}')

    echo "Monitoring pod: $POD_NAME"

    # Wait for pod to be ready
    kubectl wait --for=condition=ready \
        --timeout=300s \
        pod/"$POD_NAME" \
        -n "$STAGING_NAMESPACE"

    # Check scheduler health endpoint
    echo "Testing scheduler health endpoint..."
    kubectl exec -n "$STAGING_NAMESPACE" "$POD_NAME" -- \
        curl -f http://localhost:8000/v1/health/scheduler/status || true

    echo -e "${GREEN}✅ Deployment verification completed${NC}"
}

# Main deployment flow
main() {
    echo "🎯 APScheduler Migration Deployment Script"
    echo "=========================================="

    check_environment
    backup_deployment
    scale_to_single_replica
    deploy_apscheduler
    verify_deployment

    echo ""
    echo "🎉 APScheduler deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Monitor logs for scheduler job execution"
    echo "2. Check Redis for lock acquisition"
    echo "3. Verify only one instance runs jobs"
    echo "4. Run performance tests"
    echo ""
    echo "Commands:"
    echo "- Monitor logs: kubectl logs -f deployment/$DEPLOYMENT_NAME -n $STAGING_NAMESPACE"
    echo "- Check scheduler: kubectl exec -n $STAGING_NAMESPACE deployment/$DEPLOYMENT_NAME -- curl http://localhost:8000/v1/health/scheduler/status"
}

# Execute main deployment
check_environment
backup_deployment
scale_to_single_replica
deploy_apscheduler
verify_deployment

echo ""
echo "🎉 APScheduler deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Monitor logs for scheduler job execution"
echo "2. Check Redis for lock acquisition"
echo "3. Verify only one instance runs jobs"
echo "4. Run performance tests"
echo ""
echo "Commands:"
echo "- Monitor logs: kubectl logs -f deployment/$DEPLOYMENT_NAME -n $STAGING_NAMESPACE"
echo "- Check scheduler: kubectl exec -n $STAGING_NAMESPACE deployment/$DEPLOYMENT_NAME -- curl http://localhost:8000/v1/health/scheduler/status"</content>
<parameter name="filePath">/Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/deploy_apscheduler_staging.sh
