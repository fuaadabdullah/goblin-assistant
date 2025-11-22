#!/bin/bash
# Goblin Assistant Nginx Deployment Script
# Deploys nginx configuration to production environment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NGINX_CONF_DIR="$PROJECT_ROOT/infra/nginx"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
DOMAIN="${DOMAIN:-goblin-assistant.com}"
SSL_CERT_PATH="${SSL_CERT_PATH:-/etc/ssl/certs/goblin-assistant.crt}"
SSL_KEY_PATH="${SSL_KEY_PATH:-/etc/ssl/private/goblin-assistant.key}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if running as root or with sudo
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

# Validate environment
validate_environment() {
    log_info "Validating deployment environment..."

    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        log_error "nginx is not installed. Please install nginx first."
        exit 1
    fi

    # Check if configuration file exists
    if [[ ! -f "$NGINX_CONF_DIR/goblin-assistant.conf" ]]; then
        log_error "Nginx configuration file not found: $NGINX_CONF_DIR/goblin-assistant.conf"
        exit 1
    fi

    # Check SSL certificates for production
    if [[ "$DEPLOY_ENV" == "production" ]]; then
        if [[ ! -f "$SSL_CERT_PATH" ]]; then
            log_warn "SSL certificate not found: $SSL_CERT_PATH"
            log_warn "Make sure to obtain SSL certificates before deploying to production"
        fi
        if [[ ! -f "$SSL_KEY_PATH" ]]; then
            log_warn "SSL private key not found: $SSL_KEY_PATH"
            log_warn "Make sure to obtain SSL certificates before deploying to production"
        fi
    fi

    log_success "Environment validation passed"
}

# Backup existing configuration
backup_existing_config() {
    log_info "Backing up existing nginx configuration..."

    local backup_dir="/etc/nginx/backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    if [[ -f "/etc/nginx/sites-enabled/goblin-assistant.conf" ]]; then
        cp "/etc/nginx/sites-enabled/goblin-assistant.conf" "$backup_dir/"
        log_info "Backed up existing configuration to: $backup_dir"
    else
        log_info "No existing configuration found to backup"
    fi
}

# Generate production configuration
generate_prod_config() {
    log_info "Generating production nginx configuration..."

    local template_file="$NGINX_CONF_DIR/goblin-assistant.prod.conf"
    local temp_config="/tmp/goblin-assistant.conf"

    # Copy template
    cp "$template_file" "$temp_config"

    # Replace placeholders for production
    if [[ "$DEPLOY_ENV" == "production" ]]; then
        # Update server name
        sed -i "s/server_name your-domain.com;/server_name $DOMAIN;/" "$temp_config"

        # Update SSL paths
        sed -i "s|/path/to/ssl/cert.pem|$SSL_CERT_PATH|g" "$temp_config"
        sed -i "s|/path/to/ssl/private.key|$SSL_KEY_PATH|g" "$temp_config"

        # Update static files path (adjust as needed)
        sed -i "s|/path/to/static/files/|$PROJECT_ROOT/goblin-assistant/dist/|g" "$temp_config"
    fi

    echo "$temp_config"
}

# Deploy configuration
deploy_config() {
    local config_file="$1"

    log_info "Deploying nginx configuration..."

    # Copy to sites-available
    cp "$config_file" "/etc/nginx/sites-available/goblin-assistant.conf"

    # Enable site
    ln -sf "/etc/nginx/sites-available/goblin-assistant.conf" "/etc/nginx/sites-enabled/goblin-assistant.conf"

    # Remove default site if it exists
    if [[ -L "/etc/nginx/sites-enabled/default" ]]; then
        rm -f "/etc/nginx/sites-enabled/default"
    fi

    log_success "Configuration deployed successfully"
}

# Test configuration
test_config() {
    log_info "Testing nginx configuration..."

    if nginx -t; then
        log_success "Nginx configuration test passed"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

# Reload nginx
reload_nginx() {
    log_info "Reloading nginx..."

    if systemctl reload nginx; then
        log_success "Nginx reloaded successfully"
    else
        log_error "Failed to reload nginx"
        exit 1
    fi
}

# Health check
health_check() {
    log_info "Performing health check..."

    local max_attempts=10
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts..."

        if curl -s -f "http://localhost/api/health" > /dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        fi

        sleep 2
        ((attempt++))
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Main deployment function
main() {
    log_info "Starting Goblin Assistant nginx deployment..."
    log_info "Environment: $DEPLOY_ENV"
    log_info "Domain: $DOMAIN"

    check_privileges
    validate_environment
    backup_existing_config

    local prod_config
    prod_config=$(generate_prod_config)

    deploy_config "$prod_config"
    test_config
    reload_nginx

    if health_check; then
        log_success "Deployment completed successfully!"
        log_info "Goblin Assistant is now running at: http://$DOMAIN"
        if [[ "$DEPLOY_ENV" == "production" ]]; then
            log_info "HTTPS is configured for: https://$DOMAIN"
        fi
    else
        log_error "Deployment completed but health check failed"
        log_warn "Please check the application logs and nginx error logs"
        exit 1
    fi

    # Cleanup
    rm -f "$prod_config"
}

# Show usage
usage() {
    cat << EOF
Goblin Assistant Nginx Deployment Script

Usage: $0 [OPTIONS]

Options:
    -e, --env ENV          Deployment environment (default: production)
    -d, --domain DOMAIN    Domain name (default: goblin-assistant.com)
    --ssl-cert PATH        Path to SSL certificate
    --ssl-key PATH         Path to SSL private key
    -h, --help            Show this help message

Environment Variables:
    DEPLOY_ENV             Deployment environment
    DOMAIN                 Domain name
    SSL_CERT_PATH          Path to SSL certificate
    SSL_KEY_PATH           Path to SSL private key

Examples:
    $0 --env staging --domain staging.goblin-assistant.com
    $0 --ssl-cert /etc/ssl/certs/wildcard.crt --ssl-key /etc/ssl/private/wildcard.key

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            DEPLOY_ENV="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        --ssl-cert)
            SSL_CERT_PATH="$2"
            shift 2
            ;;
        --ssl-key)
            SSL_KEY_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
