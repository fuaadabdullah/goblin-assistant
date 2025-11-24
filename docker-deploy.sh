#!/bin/bash
# Goblin Assistant Docker Build and Deploy Script

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
IMAGE_NAME="goblin-assistant"
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-}"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
}

# Build Docker image
build_image() {
    log_info "Building Docker image: $IMAGE_NAME:$TAG"

    if [ -n "$REGISTRY" ]; then
        FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"
    else
        FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"
    fi

    docker build -t "$FULL_IMAGE_NAME" .

    log_success "Built image: $FULL_IMAGE_NAME"
}

# Push to registry
push_image() {
    if [ -z "$REGISTRY" ]; then
        log_warn "No registry specified, skipping push"
        return
    fi

    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"

    log_info "Pushing image to registry: $FULL_IMAGE_NAME"
    docker push "$FULL_IMAGE_NAME"
    log_success "Pushed image: $FULL_IMAGE_NAME"
}

# Run locally with docker-compose
run_local() {
    log_info "Starting Goblin Assistant with docker-compose"

    # Create logs directory if it doesn't exist
    mkdir -p logs

    # Start services
    docker-compose up -d

    log_success "Goblin Assistant is running!"
    log_info "Frontend: http://localhost"
    log_info "API: http://localhost:3001"
    log_info "Health check: http://localhost/api/health"
}

# Stop local services
stop_local() {
    log_info "Stopping Goblin Assistant"
    docker-compose down
    log_success "Stopped Goblin Assistant"
}

# Show usage
usage() {
    echo "Goblin Assistant Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build     Build Docker image"
    echo "  push      Push image to registry"
    echo "  deploy    Build and push image"
    echo "  run       Run locally with docker-compose"
    echo "  stop      Stop local docker-compose services"
    echo "  logs      Show logs from running containers"
    echo "  clean     Remove built images and containers"
    echo ""
    echo "Options:"
    echo "  -t TAG    Docker image tag (default: latest)"
    echo "  -r REGISTRY  Docker registry URL"
    echo "  -h         Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 build -t v1.0.0"
    echo "  $0 deploy -r myregistry.com -t v1.0.0"
    echo "  $0 run"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            COMMAND="$1"
            shift
            ;;
    esac
done

# Main logic
case "${COMMAND:-}" in
    build)
        check_docker
        build_image
        ;;
    push)
        check_docker
        push_image
        ;;
    deploy)
        check_docker
        build_image
        push_image
        ;;
    run)
        check_docker
        run_local
        ;;
    stop)
        check_docker
        stop_local
        ;;
    logs)
        check_docker
        log_info "Showing logs..."
        docker-compose logs -f
        ;;
    clean)
        check_docker
        log_info "Cleaning up Docker resources..."
        docker-compose down --volumes --remove-orphans 2>/dev/null || true
        docker image rm "$IMAGE_NAME:$TAG" 2>/dev/null || true
        docker system prune -f
        log_success "Cleanup complete"
        ;;
    *)
        log_error "Unknown command: ${COMMAND:-}"
        echo ""
        usage
        exit 1
        ;;
esac
