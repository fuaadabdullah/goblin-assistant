#!/bin/bash

# Goblin Assistant Production Deployment Script
# This script builds and deploys the application to various hosting platforms

set -e

echo "🚀 Starting Goblin Assistant Production Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."

    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js first."
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi

    print_status "Dependencies check passed ✓"
}

# Build the application
build_app() {
    print_status "Building production application..."

    if [ ! -f ".env.production" ]; then
        print_warning ".env.production not found. Using default production settings."
        print_warning "Make sure to configure your production environment variables."
    fi

    npm run build

    if [ $? -eq 0 ]; then
        print_status "Build completed successfully ✓"
    else
        print_error "Build failed!"
        exit 1
    fi
}

# Deploy to Vercel
deploy_vercel() {
    print_status "Deploying to Vercel..."

    if ! command -v vercel &> /dev/null; then
        print_status "Installing Vercel CLI..."
        npm i -g vercel
    fi

    vercel --prod --yes

    print_status "Vercel deployment completed ✓"
}

# Deploy to Netlify
deploy_netlify() {
    print_status "Deploying to Netlify..."

    # Check if netlify.toml exists
    if [ ! -f "netlify.toml" ]; then
        print_error "netlify.toml not found. Please ensure Netlify configuration is set up."
        exit 1
    fi

    # Install Netlify CLI if not present
    if ! command -v netlify &> /dev/null; then
        print_status "Installing Netlify CLI..."
        npm i -g netlify-cli
    fi

    # Check if already logged in to Netlify
    if ! netlify status &> /dev/null; then
        print_warning "Not logged in to Netlify. Please run 'netlify login' first."
        print_status "After logging in, run this script again."
        exit 1
    fi

    # Determine environment
    local ENV_TYPE="production"
    if [ "$1" = "staging" ]; then
        ENV_TYPE="staging"
        print_status "Deploying to Netlify staging environment..."
    else
        print_status "Deploying to Netlify production..."
    fi

    # Set environment variables based on deployment type
    if [ "$ENV_TYPE" = "staging" ]; then
        export VITE_DD_ENV="staging"
        # Load staging environment variables if they exist
        if [ -f ".env.staging" ]; then
            export $(grep -v '^#' .env.staging | xargs)
        fi
    else
        export VITE_DD_ENV="production"
        # Load production environment variables if they exist
        if [ -f ".env.production" ]; then
            export $(grep -v '^#' .env.production | xargs)
        fi
    fi

    # Deploy to Netlify
    if [ "$ENV_TYPE" = "staging" ]; then
        netlify deploy --dir=dist --alias staging --yes
    else
        netlify deploy --prod --dir=dist --yes
    fi

    if [ $? -eq 0 ]; then
        print_status "Netlify deployment completed ✓"
        print_status "Site URL will be shown above"
    else
        print_error "Netlify deployment failed!"
        exit 1
    fi
}

# Deploy to GitHub Pages
deploy_github_pages() {
    print_status "Deploying to GitHub Pages..."

    if ! command -v gh-pages &> /dev/null; then
        print_status "Installing gh-pages..."
        npm i -g gh-pages
    fi

    gh-pages -d dist

    print_status "GitHub Pages deployment completed ✓"
}

# Test the build locally
test_build() {
    print_status "Testing production build locally..."

    # Start preview server in background
    npx vite preview --port 4173 &
    PREVIEW_PID=$!

    # Wait a moment for server to start
    sleep 3

    # Test if server is responding
    if curl -s http://localhost:4173 > /dev/null; then
        print_status "Production build test passed ✓"
        print_status "Visit http://localhost:4173 to preview"
    else
        print_error "Production build test failed!"
        kill $PREVIEW_PID 2>/dev/null || true
        exit 1
    fi

    # Kill the preview server
    kill $PREVIEW_PID 2>/dev/null || true
}

# Main deployment function
main() {
    echo "Goblin Assistant Production Deployment Script"
    echo "============================================"

    # Parse command line arguments
    DEPLOY_TARGET=${1:-"test"}

    check_dependencies
    build_app

    case $DEPLOY_TARGET in
        "vercel")
            deploy_vercel
            ;;
        "netlify")
            deploy_netlify "production"
            ;;
        "netlify-staging")
            deploy_netlify "staging"
            ;;
        "github")
            deploy_github_pages
            ;;
        "test")
            test_build
            ;;
        *)
            print_error "Invalid deployment target: $DEPLOY_TARGET"
            echo "Usage: $0 [vercel|netlify|netlify-staging|github|test]"
            echo "  vercel          - Deploy to Vercel production"
            echo "  netlify         - Deploy to Netlify production"
            echo "  netlify-staging - Deploy to Netlify staging"
            echo "  github          - Deploy to GitHub Pages"
            echo "  test            - Test build locally (default)"
            exit 1
            ;;
    esac

    print_status "🎉 Deployment completed successfully!"
    print_status "Don't forget to:"
    print_status "  1. Update your backend URL in .env.production"
    print_status "  2. Ensure your FastAPI backend is deployed"
    print_status "  3. Configure CORS on your backend if needed"
}

# Run main function with all arguments
main "$@"
