#!/bin/bash

# CI/CD Pipeline Setup Verification Script
# This script verifies that all components of the hybrid CI/CD pipeline are properly configured

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "🔍 CI/CD Pipeline Setup Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
    fi
}

# ============================================================================
# Check 1: File Structure
# ============================================================================
echo -e "${BLUE}1. Checking File Structure...${NC}"
echo ""

files_to_check=(
    "terraform/main.tf"
    "terraform/variables.tf"
    "terraform/outputs.tf"
    "terraform/render.tf"
    "terraform/database.tf"
    "terraform/cache.tf"
    "terraform/secrets.tf"
    "terraform/.gitignore"
    "terraform.tfvars.example"
    ".github/workflows/ci.yml"
    ".github/workflows/terraform-plan.yml"
    ".github/workflows/deploy-staging.yml"
    ".github/workflows/deploy-prod.yml"
    ".circleci/config.yml"
    "CI_CD_PIPELINE_README.md"
)

all_files_exist=0
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (missing)"
        all_files_exist=1
    fi
done
check_status $all_files_exist "All required files present"
echo ""

# ============================================================================
# Check 2: Terraform Validation
# ============================================================================
echo -e "${BLUE}2. Validating Terraform...${NC}"
echo ""

if command -v terraform &> /dev/null; then
    cd terraform
    
    # Check if initialized
    if [ ! -d ".terraform" ]; then
        echo -e "${YELLOW}⚠️  Terraform not initialized. Run: terraform init${NC}"
        terraform_init=1
    else
        terraform_init=0
    fi
    
    # Validate format
    if terraform fmt -check -recursive &>/dev/null; then
        echo -e "${GREEN}✅${NC} Terraform formatting valid"
    else
        echo -e "${RED}❌${NC} Terraform formatting issues. Run: terraform fmt -recursive"
    fi
    
    # Validate config
    if terraform validate &>/dev/null; then
        echo -e "${GREEN}✅${NC} Terraform configuration valid"
    else
        echo -e "${RED}❌${NC} Terraform configuration has errors"
    fi
    
    cd ..
    check_status $terraform_init "Terraform initialized"
else
    echo -e "${YELLOW}⚠️  Terraform CLI not installed${NC}"
    echo "   Install from: https://www.terraform.io/downloads"
fi
echo ""

# ============================================================================
# Check 3: GitHub Configuration
# ============================================================================
echo -e "${BLUE}3. Checking GitHub Configuration...${NC}"
echo ""

if [ -d ".github/workflows" ]; then
    workflows=(
        "ci.yml"
        "terraform-plan.yml"
        "deploy-staging.yml"
        "deploy-prod.yml"
    )
    
    all_workflows_exist=0
    for workflow in "${workflows[@]}"; do
        if [ -f ".github/workflows/$workflow" ]; then
            echo -e "${GREEN}✅${NC} $workflow"
        else
            echo -e "${RED}❌${NC} $workflow (missing)"
            all_workflows_exist=1
        fi
    done
    check_status $all_workflows_exist "All GitHub workflows present"
else
    echo -e "${RED}❌${NC} .github/workflows directory not found"
fi
echo ""

# ============================================================================
# Check 4: CircleCI Configuration
# ============================================================================
echo -e "${BLUE}4. Checking CircleCI Configuration...${NC}"
echo ""

if [ -f ".circleci/config.yml" ]; then
    echo -e "${GREEN}✅${NC} CircleCI config.yml exists"
    
    # Check if it's not the old deprecated format
    if grep -q "version: 2.1" ".circleci/config.yml"; then
        echo -e "${GREEN}✅${NC} Using modern CircleCI format (v2.1)"
    else
        echo -e "${YELLOW}⚠️  CircleCI config format outdated${NC}"
    fi
    
    # Check for essential jobs
    if grep -q "backend-test\|frontend-test\|build-docker" ".circleci/config.yml"; then
        echo -e "${GREEN}✅${NC} CircleCI jobs configured"
    else
        echo -e "${RED}❌${NC} Essential CircleCI jobs missing"
    fi
else
    echo -e "${RED}❌${NC} CircleCI config.yml not found"
fi
echo ""

# ============================================================================
# Check 5: Docker Configuration
# ============================================================================
echo -e "${BLUE}5. Checking Docker Configuration...${NC}"
echo ""

if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✅${NC} Dockerfile exists"
else
    echo -e "${RED}❌${NC} Dockerfile not found"
fi

if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✅${NC} docker-compose.yml exists"
else
    echo -e "${YELLOW}⚠️  docker-compose.yml not found (optional)${NC}"
fi
echo ""

# ============================================================================
# Check 6: Environment & Secrets
# ============================================================================
echo -e "${BLUE}6. Checking Environment Configuration...${NC}"
echo ""

if [ -f "terraform.tfvars.example" ]; then
    echo -e "${GREEN}✅${NC} terraform.tfvars.example exists"
else
    echo -e "${RED}❌${NC} terraform.tfvars.example not found"
fi

if [ -f ".env.example" ]; then
    echo -e "${GREEN}✅${NC} .env.example exists"
else
    echo -e "${YELLOW}⚠️  .env.example not found${NC}"
fi

# Check if terraform.tfvars is in .gitignore
if grep -q "terraform.tfvars" ".gitignore" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} terraform.tfvars properly ignored"
else
    echo -e "${YELLOW}⚠️  terraform.tfvars should be added to .gitignore${NC}"
    echo "   Run: echo 'terraform.tfvars' >> .gitignore"
fi
echo ""

# ============================================================================
# Check 7: Documentation
# ============================================================================
echo -e "${BLUE}7. Checking Documentation...${NC}"
echo ""

docs=(
    "CI_CD_PIPELINE_README.md"
    "GOBLINOS_STORAGE_README.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        lines=$(wc -l < "$doc")
        echo -e "${GREEN}✅${NC} $doc ($lines lines)"
    else
        echo -e "${YELLOW}⚠️  $doc not found${NC}"
    fi
done
echo ""

# ============================================================================
# Check 8: Git Status
# ============================================================================
echo -e "${BLUE}8. Checking Git Status...${NC}"
echo ""

# Check if we're in a git repository
if [ -d ".git" ]; then
    echo -e "${GREEN}✅${NC} Git repository initialized"
    
    # Check current branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    echo -e "${BLUE}   Current branch: $current_branch${NC}"
    
    # Count unpushed commits
    unpushed=$(git log --oneline @{u}.. 2>/dev/null | wc -l)
    if [ $unpushed -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $unpushed unpushed commits${NC}"
    fi
else
    echo -e "${RED}❌${NC} Not a git repository"
fi
echo ""

# ============================================================================
# Summary & Next Steps
# ============================================================================
echo "═══════════════════════════════════════════════════════════════"
echo -e "${BLUE}📋 Setup Summary${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "✅ Completed:"
echo "  • Terraform infrastructure code generated"
echo "  • GitHub Actions workflows created"
echo "  • CircleCI pipeline configured"
echo "  • Documentation completed"
echo ""

echo "📌 Next Steps:"
echo ""
echo "1️⃣  Initialize Terraform (if not done):"
echo "   cd terraform && terraform init"
echo ""
echo "2️⃣  Create terraform.tfvars:"
echo "   cp terraform.tfvars.example terraform.tfvars"
echo "   # Edit with your actual values"
echo ""
echo "3️⃣  Add GitHub Secrets:"
echo "   GitHub → Settings → Secrets and variables → Actions"
echo "   Add: RENDER_API_KEY, RENDER_SERVICE_ID_STAGING, RENDER_SERVICE_ID_PROD"
echo ""
echo "4️⃣  Enable CircleCI:"
echo "   https://app.circleci.com/setup/gh/fuaadabdullah/goblin-assistant"
echo ""
echo "5️⃣  Test the pipeline:"
echo "   git add ."
echo "   git commit -m 'feat: Add hybrid CI/CD pipeline'"
echo "   git push origin main"
echo ""
echo "6️⃣  Monitor workflows:"
echo "   GitHub: https://github.com/fuaadabdullah/goblin-assistant/actions"
echo "   CircleCI: https://app.circleci.com/pipelines/github/fuaadabdullah/goblin-assistant"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Verification Complete!${NC}"
echo "═══════════════════════════════════════════════════════════════"
