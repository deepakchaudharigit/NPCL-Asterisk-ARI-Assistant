# 🚀 NPCL Voice Assistant - Deployment Guide

## 📋 Overview

This guide provides comprehensive instructions for deploying the NPCL Voice Assistant in various environments, from development to production.

## 🏗️ Deployment Options

### 1. Docker Compose (Recommended for Development)
### 2. Kubernetes (Recommended for Production)
### 3. Manual Installation
### 4. Cloud Deployment (AWS, GCP, Azure)

---

## 🐳 Docker Compose Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 20GB disk space

### Quick Start

```bash
# Clone the repository
git clone https://github.com/npcl/voice-assistant.git
cd voice-assistant

# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env

# Start services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose ps
```

### Environment Configuration

Create `.env` file with required variables:

```bash
# Required - Google AI API Key
GOOGLE_API_KEY=your-actual-google-api-key-here

# Database
DB_PASSWORD=secure-database-password
REDIS_PASSWORD=secure-redis-password

# Security
ARI_PASSWORD=secure-ari-password
GRAFANA_PASSWORD=secure-grafana-password

# Optional - Customization
ASSISTANT_NAME="NPCL Assistant"
LOG_LEVEL=INFO
VERSION=latest
```

### Service URLs

After deployment, services will be available at:

- **Voice Assistant API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Grafana Dashboard**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:9090

---

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)
- 8GB RAM minimum
- 50GB disk space

### Namespace Setup

```bash
# Create namespace
kubectl create namespace voice-assistant

# Set as default
kubectl config set-context --current --namespace=voice-assistant
```

### Secret Management

```bash
# Create secrets
kubectl create secret generic voice-assistant-secrets \
  --from-literal=google-api-key="your-google-api-key" \
  --from-literal=db-password="secure-db-password" \
  --from-literal=redis-password="secure-redis-password"

# Create TLS secret (if using HTTPS)
kubectl create secret tls voice-assistant-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

### ConfigMap

```yaml
# config-map.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: voice-assistant-config
  namespace: voice-assistant
data:
  ASSISTANT_NAME: "NPCL Assistant"
  LOG_LEVEL: "INFO"
  AUDIO_SAMPLE_RATE: "16000"
  MAX_CALL_DURATION: "3600"
  ENABLE_PERFORMANCE_MONITORING: "true"
```

### Deployment Manifests

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-assistant
  namespace: voice-assistant
  labels:
    app: voice-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: voice-assistant
  template:
    metadata:
      labels:
        app: voice-assistant
    spec:
      containers:
      - name: voice-assistant
        image: npcl/voice-assistant:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: voice-assistant-secrets
              key: google-api-key
        - name: DATABASE_URL
          value: "postgresql://voiceassistant:$(DB_PASSWORD)@postgres:5432/voiceassistant"
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@redis:6379/0"
        envFrom:
        - configMapRef:
            name: voice-assistant-config
        - secretRef:
            name: voice-assistant-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: audio-storage
          mountPath: /app/sounds
        - name: recordings-storage
          mountPath: /app/recordings
      volumes:
      - name: audio-storage
        persistentVolumeClaim:
          claimName: audio-pvc
      - name: recordings-storage
        persistentVolumeClaim:
          claimName: recordings-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: voice-assistant-service
  namespace: voice-assistant
spec:
  selector:
    app: voice-assistant
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: voice-assistant-ingress
  namespace: voice-assistant
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.voice-assistant.com
    secretName: voice-assistant-tls
  rules:
  - host: api.voice-assistant.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: voice-assistant-service
            port:
              number: 80
```

### Persistent Storage

```yaml
# storage.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: audio-pvc
  namespace: voice-assistant
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: recordings-pvc
  namespace: voice-assistant
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
  storageClassName: standard
```

### Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f config-map.yaml
kubectl apply -f storage.yaml
kubectl apply -f deployment.yaml

# Check deployment status
kubectl get pods
kubectl get services
kubectl get ingress

# View logs
kubectl logs -f deployment/voice-assistant

# Scale deployment
kubectl scale deployment voice-assistant --replicas=5
```

---

## 🌩️ Cloud Deployment

### AWS Deployment

#### EKS Setup

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create EKS cluster
eksctl create cluster \
  --name voice-assistant-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 10 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --region us-west-2 --name voice-assistant-cluster
```

#### RDS Database

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier voice-assistant-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username voiceassistant \
  --master-user-password SecurePassword123 \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-12345678 \
  --db-subnet-group-name default
```

#### ElastiCache Redis

```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id voice-assistant-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

### GCP Deployment

#### GKE Setup

```bash
# Create GKE cluster
gcloud container clusters create voice-assistant-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials voice-assistant-cluster --zone us-central1-a
```

#### Cloud SQL

```bash
# Create Cloud SQL instance
gcloud sql instances create voice-assistant-db \
  --database-version POSTGRES_13 \
  --tier db-f1-micro \
  --region us-central1
```

### Azure Deployment

#### AKS Setup

```bash
# Create resource group
az group create --name voice-assistant-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group voice-assistant-rg \
  --name voice-assistant-cluster \
  --node-count 3 \
  --node-vm-size Standard_B2s \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group voice-assistant-rg --name voice-assistant-cluster
```

---

## 🔧 Manual Installation

### System Requirements

- Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Nginx 1.18+
- 8GB RAM minimum
- 50GB disk space

### Installation Steps

#### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv \
  postgresql postgresql-contrib redis-server nginx \
  portaudio19-dev python3-pyaudio ffmpeg curl

# Create user
sudo useradd -m -s /bin/bash voiceassistant
sudo usermod -aG sudo voiceassistant
```

#### 2. Database Setup

```bash
# Configure PostgreSQL
sudo -u postgres psql
CREATE DATABASE voiceassistant;
CREATE USER voiceassistant WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE voiceassistant TO voiceassistant;
\q

# Configure Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### 3. Application Setup

```bash
# Switch to application user
sudo su - voiceassistant

# Clone repository
git clone https://github.com/npcl/voice-assistant.git
cd voice-assistant

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit configuration

# Create directories
mkdir -p sounds/temp recordings logs

# Run database migrations
python -m src.database.migrate

# Test installation
python src/main.py --test
```

#### 4. Service Configuration

```bash
# Create systemd service
sudo tee /etc/systemd/system/voice-assistant.service > /dev/null <<EOF
[Unit]
Description=NPCL Voice Assistant
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=voiceassistant
Group=voiceassistant
WorkingDirectory=/home/voiceassistant/voice-assistant
Environment=PATH=/home/voiceassistant/voice-assistant/.venv/bin
ExecStart=/home/voiceassistant/voice-assistant/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable voice-assistant
sudo systemctl start voice-assistant
```

#### 5. Nginx Configuration

```bash
# Configure Nginx
sudo tee /etc/nginx/sites-available/voice-assistant > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/voice-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📊 Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'voice-assistant'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import the provided dashboard JSON:

```bash
# Import dashboard
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/voice-assistant-dashboard.json
```

### Log Aggregation

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  fields:
    service: voice-assistant
  fields_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

---

## 🔒 Security Hardening

### SSL/TLS Configuration

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Firewall Configuration

```bash
# Configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Security Headers

```nginx
# Add to Nginx configuration
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
add_header Content-Security-Policy "default-src 'self'";
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
sudo journalctl -u voice-assistant -f

# Check configuration
python src/main.py --validate-config

# Check dependencies
pip check
```

#### 2. Database Connection Issues

```bash
# Test database connection
psql -h localhost -U voiceassistant -d voiceassistant

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### 3. Audio Processing Issues

```bash
# Check audio devices
aplay -l
arecord -l

# Test audio processing
python -c "import pyaudio; print('PyAudio OK')"
```

#### 4. High Memory Usage

```bash
# Monitor memory
htop
free -h

# Check for memory leaks
python -m memory_profiler src/main.py
```

### Performance Tuning

#### Database Optimization

```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

#### Redis Optimization

```bash
# Redis configuration
echo 'maxmemory 512mb' >> /etc/redis/redis.conf
echo 'maxmemory-policy allkeys-lru' >> /etc/redis/redis.conf
sudo systemctl restart redis
```

#### Application Tuning

```bash
# Environment variables for performance
export PYTHONOPTIMIZE=1
export UVICORN_WORKERS=4
export UVICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
```

---

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale Kubernetes deployment
kubectl scale deployment voice-assistant --replicas=10

# Add load balancer
kubectl expose deployment voice-assistant --type=LoadBalancer --port=80
```

### Vertical Scaling

```yaml
# Increase resource limits
resources:
  requests:
    memory: "2Gi"
    cpu: "1"
  limits:
    memory: "8Gi"
    cpu: "4"
```

### Database Scaling

```bash
# PostgreSQL read replicas
# Configure streaming replication
# Use connection pooling (PgBouncer)

# Redis clustering
# Configure Redis Cluster mode
# Use Redis Sentinel for HA
```

---

## 🔄 Backup and Recovery

### Database Backup

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -h localhost -U voiceassistant voiceassistant > \
  "$BACKUP_DIR/voiceassistant_$DATE.sql"

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
```

### Application Backup

```bash
# Backup configuration and data
tar -czf voice-assistant-backup-$(date +%Y%m%d).tar.gz \
  /home/voiceassistant/voice-assistant \
  /etc/systemd/system/voice-assistant.service \
  /etc/nginx/sites-available/voice-assistant
```

### Disaster Recovery

```bash
# Recovery procedure
1. Restore database from backup
2. Restore application files
3. Restart services
4. Verify functionality
```

---

## 📞 Support

For deployment support:

- **Documentation**: [https://docs.npcl-voice-assistant.com](https://docs.npcl-voice-assistant.com)
- **GitHub Issues**: [https://github.com/npcl/voice-assistant/issues](https://github.com/npcl/voice-assistant/issues)
- **Email**: deployment-support@npcl-voice-assistant.com
- **Slack**: #deployment-help

---

*Last updated: January 15, 2024*