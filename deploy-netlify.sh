#!/bin/bash

# Netlify Deployment Script for Goblin Assistant
# This script handles Netlify deployments with proper environment configuration

set -e

echo "🚀 Goblin Assistant - Netlify Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check dependencies
check_dependencies() {
    print_step "Checking dependencies..."

    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        exit 1
    fi

    if ! command -v netlify &> /dev/null; then
        print_status "Installing Netlify CLI..."
        npm i -g netlify-cli
    fi

    print_status "Dependencies check passed ✓"
}

# Check Netlify authentication
check_netlify_auth() {
    print_step "Checking Netlify authentication..."

    # Check if netlify status shows we're logged in
    if netlify status 2>&1 | grep -q "Email:"; then
        print_status "Netlify authentication confirmed ✓"
    else
        print_error "Not logged in to Netlify"
        print_status "Please run: netlify login"
        exit 1
    fi
}

# Build the application
build_app() {
    local env_type=$1

    print_step "Building application for $env_type..."

    # Set environment variables based on deployment type
    if [ "$env_type" = "staging" ]; then
        export VITE_DD_ENV="staging"
        if [ -f ".env.staging" ]; then
            export $(grep -v '^#' .env.staging | xargs)
        fi
    else
        export VITE_DD_ENV="production"
        if [ -f ".env.production" ]; then
            export $(grep -v '^#' .env.production | xargs)
        fi
    fi

    # Build the application
    npm run build

    if [ $? -eq 0 ]; then
        print_status "Build completed successfully ✓"
    else
        print_error "Build failed!"
        exit 1
    fi
}

# Deploy to Netlify
deploy_to_netlify() {
    local env_type=$1

    print_step "Deploying to Netlify $env_type..."

    # Check if site is already linked
    if ! netlify status 2>&1 | grep -q "Site ID:"; then
        print_status "No site linked. Creating new Netlify site..."

        # Create a new site
        SITE_NAME="goblin-assistant-${env_type}"
        if [ "$env_type" = "staging" ]; then
            SITE_NAME="goblin-assistant-staging"
        else
            SITE_NAME="goblin-assistant"
        fi

        print_status "Creating site: $SITE_NAME"
        netlify sites:create --name "$SITE_NAME"

        if [ $? -ne 0 ]; then
            print_error "Failed to create Netlify site"
            exit 1
        fi

        print_status "Site created successfully ✓"
    fi

    if [ "$env_type" = "staging" ]; then
        # Deploy to staging branch/alias
        netlify deploy --dir=dist --alias staging
    else
        # Deploy to production
        netlify deploy --prod --dir=dist
    fi

    if [ $? -eq 0 ]; then
        print_status "Netlify deployment completed ✓"
    else
        print_error "Netlify deployment failed!"
        exit 1
    fi
}

# Setup environment variables in Netlify
setup_netlify_env() {
    local env_type=$1

    print_step "Setting up environment variables in Netlify..."

    if [ "$env_type" = "staging" ]; then
        ENV_FILE=".env.staging"
        CONTEXT="branch-deploy"
    else
        ENV_FILE=".env.production"
        CONTEXT="production"
    fi

    if [ -f "$ENV_FILE" ]; then
        print_status "Setting environment variables from $ENV_FILE..."

        # Read environment variables and set them in Netlify
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue

            # Remove VITE_ prefix for Netlify (it adds it automatically for client-side vars)
            if [[ $key == VITE_* ]]; then
                netlify env:set "$key" "$value" --context "$CONTEXT" --yes 2>/dev/null || true
            fi
        done < "$ENV_FILE"

        print_status "Environment variables configured ✓"
    else
        print_warning "$ENV_FILE not found. Please create it with your environment variables."
    fi
}

# Main deployment function
main() {
    local env_type="production"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --staging)
                env_type="staging"
                shift
                ;;
            --help)
                echo "Usage: $0 [--staging] [--setup-env]"
                echo ""
                echo "Options:"
                echo "  --staging     Deploy to staging environment"
                echo "  --setup-env   Only setup environment variables, don't deploy"
                echo "  --help        Show this help"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    echo "Environment: $env_type"
    echo "=================="

    check_dependencies
    check_netlify_auth
    build_app "$env_type"
    deploy_to_netlify "$env_type"

    echo ""
    print_status "🎉 Deployment completed successfully!"
    echo ""
    print_status "Next steps:"
    echo "1. Visit the deployment URL shown above"
    echo "2. Check Datadog RUM dashboard for user sessions"
    echo "3. Verify error tracking is working"
    echo "4. Test API integrations"
}

# Run main function
main "$@"
