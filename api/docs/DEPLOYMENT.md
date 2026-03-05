# Deployment Guide

This document provides comprehensive guidance for deploying the Goblin Assistant Backend API to various environments and platforms.

## Overview

The Goblin Assistant Backend can be deployed to multiple environments:

- **Development**: Local development with SQLite
- **Staging**: Production-like environment for testing
- **Production**: High-availability, scalable production deployment
- **Cloud Platforms**: AWS, GCP, Azure, and specialized platforms

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores
- **Memory**: 4GB RAM
- **Storage**: 20GB SSD
- **Network**: 1Gbps

#### Recommended Production Requirements
- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Storage**: 100GB+ SSD
- **Network**: 10Gbps
- **Load Balancer**: For high availability

### Software Dependencies

```bash
# Required software
- Python 3.11+
- Redis 6.0+
- PostgreSQL 14+ (production)
- Docker 20.10+ (containerized deployment)
- Nginx/HAProxy (reverse proxy)
```

### Environment Variables

```bash
# Production environment variables
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
JWT_SECRET_KEY=secure-random-secret
ROUTING_ENCRYPTION_KEY=secure-encryption-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
# ... other provider keys
```

## Development Deployment

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/fuaadabdullah/forgemono.git
cd forgemono/apps/goblin-assistant/api

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python init_db.py

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development

```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=sqlite:///./dev.db
      - REDIS_URL=redis://redis:6379
    volumes:
      - .:/app
    depends_on:
      - redis
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  redis_data:
```

```bash
# Run development environment
docker-compose -f docker-compose.dev.yml up -d
```

## Production Deployment

### Single Server Deployment

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-pip python3.11-venv nginx postgresql redis-server

# Create application user
sudo useradd -r -s /bin/bash goblin
sudo mkdir -p /opt/goblin-assistant
sudo chown goblin:goblin /opt/goblin-assistant
```

#### 2. Application Setup

```bash
# Switch to application user
sudo su - goblin

# Clone repository
cd /opt/goblin-assistant
git clone https://github.com/fuaadabdullah/forgemono.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r apps/goblin-assistant/api/requirements.txt

# Set up environment
cp apps/goblin-assistant/api/.env.example .env
# Edit .env with production values
```

#### 3. Database Setup

```bash
# Switch back to sudo user
exit

# Set up PostgreSQL
sudo -u postgres psql
```

```sql
-- PostgreSQL setup
CREATE DATABASE goblin_assistant;
CREATE USER goblin_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE goblin_assistant TO goblin_user;
\q
```

#### 4. Service Configuration

```ini
# /etc/systemd/system/goblin-assistant.service
[Unit]
Description=Goblin Assistant Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=goblin
Group=goblin
WorkingDirectory=/opt/goblin-assistant
Environment=PATH=/opt/goblin-assistant/venv/bin
ExecStart=/opt/goblin-assistant/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable goblin-assistant
sudo systemctl start goblin-assistant
```

#### 5. Nginx Configuration

```nginx
# /etc/nginx/sites-available/goblin-assistant
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # API Proxy
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/goblin-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. SSL Certificate

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Set up auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Containerized Deployment

#### Docker Production Setup

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/goblin_assistant
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ROUTING_ENCRYPTION_KEY=${ROUTING_ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=goblin_assistant
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

```bash
# Deploy production environment
docker-compose -f docker-compose.prod.yml up -d
```

## Cloud Deployment

### AWS Deployment

#### ECS Fargate Deployment

```json
{
  "family": "goblin-assistant-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "goblin-assistant-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/goblin-assistant:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/db"
        }
      ],
      "secrets": [
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:ssm:region:account:parameter/goblin/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/goblin-assistant-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Terraform Infrastructure

```hcl
# main.tf
provider "aws" {
  region = var.aws_region
}

# VPC and networking
module "vpc" {
  source = "./modules/vpc"
  
  name = "goblin-assistant"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
}

# RDS PostgreSQL
module "database" {
  source = "./modules/rds"
  
  identifier = "goblin-assistant-db"
  
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  
  db_name  = "goblin_assistant"
  username = "postgres"
  password = var.db_password
  
  subnet_ids              = module.vpc.private_subnets
  vpc_security_group_ids  = [module.database_security_group.id]
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
}

# ElastiCache Redis
module "redis" {
  source = "./modules/elasticache"
  
  replication_group_id         = "goblin-assistant-redis"
  description                  = "Redis cluster for Goblin Assistant"
  
  node_type                    = "cache.t3.micro"
  port                         = 6379
  parameter_group_name         = "default.redis7"
  
  num_cache_clusters           = 2
  
  subnet_ids                   = module.vpc.private_subnets
  security_group_ids           = [module.redis_security_group.id]
  
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  auth_token                   = var.redis_auth_token
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "goblin-assistant"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "goblin-assistant-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.vpc.public_subnets

  enable_deletion_protection = false

  tags = {
    Environment = "production"
  }
}

# ECS Service
resource "aws_ecs_service" "main" {
  name            = "goblin-assistant-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = 3

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = "goblin-assistant-api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.main]
}
```

### Google Cloud Platform

#### Cloud Run Deployment

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/goblin-assistant:$BUILD_ID', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/goblin-assistant:$BUILD_ID']
  
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
    - 'run'
    - 'deploy'
    - 'goblin-assistant-api'
    - '--image'
    - 'gcr.io/$PROJECT_ID/goblin-assistant:$BUILD_ID'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
    - '--set-env-vars'
    - 'ENVIRONMENT=production,DATABASE_URL=${_DATABASE_URL}'

substitutions:
  _DATABASE_URL: "postgresql://user:pass@host:5432/db"
```

#### GKE Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: goblin-assistant-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: goblin-assistant-api
  template:
    metadata:
      labels:
        app: goblin-assistant-api
    spec:
      containers:
      - name: api
        image: gcr.io/PROJECT_ID/goblin-assistant:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
