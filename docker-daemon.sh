#!/bin/bash

# Goblin Assistant - Docker Daemon Manager for macOS
# This script helps manage Docker Desktop on macOS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker_installation() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker Desktop for Mac:"
        echo "  https://docs.docker.com/desktop/install/mac-install/"
        exit 1
    fi
    print_success "Docker is installed at: $(which docker)"
}

# Check if Docker daemon is running
check_docker_daemon() {
    if ! docker info &> /dev/null; then
        print_warning "Docker daemon is not running"
        return 1
    else
        print_success "Docker daemon is running"
        return 0
    fi
}

# Start Docker Desktop (macOS)
start_docker_desktop() {
    print_status "Attempting to start Docker Desktop..."

    # Try to start Docker Desktop app
    if command -v open &> /dev/null; then
        open -a "Docker Desktop" || true
        print_status "Opened Docker Desktop. Waiting for daemon to start..."
    else
        print_error "Cannot open Docker Desktop automatically"
        echo "Please manually start Docker Desktop from Applications"
        return 1
    fi

    # Wait for Docker daemon to be ready
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker info &> /dev/null; then
            print_success "Docker daemon is now running!"
            return 0
        fi

        print_status "Waiting for Docker daemon... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    print_error "Docker daemon failed to start within 60 seconds"
    echo "Please check Docker Desktop and try again"
    return 1
}

# Stop Docker Desktop
stop_docker_desktop() {
    print_status "Stopping Docker Desktop..."
    pkill -f "Docker Desktop" || true
    print_success "Docker Desktop stopped"
}

# Show Docker status
show_status() {
    echo "=== Docker Status ==="
    echo "Docker version: $(docker --version 2>/dev/null || echo 'Not available')"
    echo "Docker daemon: $(check_docker_daemon && echo 'Running' || echo 'Not running')"

    if check_docker_daemon; then
        echo "Docker info:"
        docker info | head -10
    fi
}

# Main script logic
case "${1:-status}" in
    "start")
        check_docker_installation
        if check_docker_daemon; then
            print_success "Docker daemon is already running"
        else
            start_docker_desktop
        fi
        ;;
    "stop")
        stop_docker_desktop
        ;;
    "restart")
        stop_docker_desktop
        sleep 2
        start_docker_desktop
        ;;
    "status")
        check_docker_installation
        show_status
        ;;
    "check")
        check_docker_installation
        if check_docker_daemon; then
            print_success "Docker is ready for use"
            exit 0
        else
            print_error "Docker daemon is not running"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|check}"
        echo ""
        echo "Commands:"
        echo "  start   - Start Docker Desktop and wait for daemon"
        echo "  stop    - Stop Docker Desktop"
        echo "  restart - Restart Docker Desktop"
        echo "  status  - Show Docker status and information"
        echo "  check   - Quick check if Docker is ready (exit code 0/1)"
        exit 1
        ;;
esac
