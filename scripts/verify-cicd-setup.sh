#!/usr/bin/env bash
set -euo pipefail

# Verify the active CI/CD shape after Terraform/Kubernetes deployment assets
# were retired. This script checks repository wiring only; it does not call
# external deployment APIs.

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

failures=0

pass() {
  echo -e "${GREEN}PASS${NC}: $1"
}

warn() {
  echo -e "${YELLOW}WARN${NC}: $1"
}

fail() {
  echo -e "${RED}FAIL${NC}: $1"
  failures=$((failures + 1))
}

require_file() {
  local path=$1
  if [ -f "$path" ]; then
    pass "$path exists"
  else
    fail "$path is missing"
  fi
}

require_absent() {
  local path=$1
  if [ -e "$path" ]; then
    fail "$path should be removed or archived"
  else
    pass "$path is absent"
  fi
}

require_grep() {
  local pattern=$1
  local path=$2
  local message=$3
  if grep -Eq "$pattern" "$path"; then
    pass "$message"
  else
    fail "$message"
  fi
}

echo -e "${BLUE}CI/CD setup verification${NC}"
echo ""

echo -e "${BLUE}1. Active workflow files${NC}"
require_file ".github/workflows/ci.yml"
require_file ".github/workflows/deploy-staging.yml"
require_file ".github/workflows/deploy-prod.yml"
require_file ".circleci/config.yml"
require_absent ".github/workflows/terraform-plan.yml"
echo ""

echo -e "${BLUE}2. Deployment authority${NC}"
require_file "render.yaml"
require_file "apps/web/vercel.json"
require_file "fly.toml"
require_grep "ARCHIVED" "fly.toml" "fly.toml is explicitly archived"
require_grep "Render \\(render.yaml\\) is the active deployment platform" "fly.toml" "fly.toml points readers to Render"
require_grep "api.render.com/v1/services" ".github/workflows/deploy-staging.yml" "staging deploy uses Render API"
require_grep "api.render.com/v1/services" ".github/workflows/deploy-prod.yml" "production deploy uses Render API"
echo ""

echo -e "${BLUE}3. Retired Terraform/Kubernetes assets${NC}"
require_absent "terraform"
require_absent "terraform.tfvars.example"
require_absent "k8s"
require_absent "kind-config.yaml"
require_absent "docker-compose.redis.yml"
require_absent "scripts/setup-deployment-credentials.sh"
require_absent "scripts/run-full-deployment-setup.sh"
echo ""

echo -e "${BLUE}4. Dependency automation${NC}"
require_file ".github/dependabot.yml"
if grep -q "package-ecosystem: terraform" ".github/dependabot.yml"; then
  fail "Dependabot still references Terraform"
else
  pass "Dependabot no longer references Terraform"
fi
for ecosystem in pip npm github-actions; do
  require_grep "package-ecosystem: ${ecosystem}" ".github/dependabot.yml" "Dependabot covers ${ecosystem}"
done
echo ""

echo -e "${BLUE}5. Docker and docs${NC}"
require_file "Dockerfile"
require_file "docker-compose.yml"
require_file "docs/operations/CI_CD_PIPELINE_README.md"
require_file "docs/operations/DEPLOYMENT_ARCHITECTURE.md"
echo ""

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  current_branch=$(git rev-parse --abbrev-ref HEAD)
  echo -e "${BLUE}Current branch:${NC} ${current_branch}"
else
  warn "Not running inside a git repository"
fi

echo ""
if [ "$failures" -eq 0 ]; then
  echo -e "${GREEN}CI/CD setup verification passed.${NC}"
else
  echo -e "${RED}CI/CD setup verification failed with ${failures} issue(s).${NC}"
fi

exit "$failures"
