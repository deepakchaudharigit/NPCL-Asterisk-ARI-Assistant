#!/usr/bin/env python3
"""
Enterprise Deployment Script for NPCL Voice Assistant
Deploys the voice assistant with full security, observability, and scalability features
"""

import asyncio
import argparse
import sys
import os
import subprocess
import time
from pathlib import Path
import yaml
import json

def run_command(command, check=True, capture_output=False):
    """Run shell command"""
    print(f"Running: {command}")
    result = subprocess.run(
        command, 
        shell=True, 
        check=check, 
        capture_output=capture_output,
        text=True
    )
    if capture_output:
        return result.stdout.strip()
    return result.returncode == 0

def check_prerequisites():
    """Check deployment prerequisites"""
    print("🔍 Checking prerequisites...")
    
    prerequisites = {
        "docker": "docker --version",
        "kubectl": "kubectl version --client",
        "python": "python --version",
        "pip": "pip --version"
    }
    
    missing = []
    for tool, command in prerequisites.items():
        try:
            run_command(command, capture_output=True)
            print(f"✅ {tool} is available")
        except subprocess.CalledProcessError:
            print(f"❌ {tool} is not available")
            missing.append(tool)
    
    if missing:
        print(f"\n❌ Missing prerequisites: {', '.join(missing)}")
        print("Please install the missing tools and try again.")
        return False
    
    print("✅ All prerequisites are available")
    return True

def setup_environment():
    """Setup environment variables and configuration"""
    print("⚙️ Setting up environment...")
    
    # Check for .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("Please copy .env.example to .env and configure your settings")
        return False
    
    # Validate required environment variables
    required_vars = [
        "GOOGLE_API_KEY",
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please configure these variables in your .env file")
        return False
    
    print("✅ Environment configuration is valid")
    return True

def build_docker_image():
    """Build Docker image"""
    print("🐳 Building Docker image...")
    
    dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    portaudio19-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements-test.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY sounds/ ./sounds/
COPY asterisk-config/ ./asterisk-config/

# Create necessary directories
RUN mkdir -p logs sounds/temp recordings

# Set environment variables
ENV PYTHONPATH=/app/src
ENV LOG_LEVEL=INFO

# Expose ports
EXPOSE 8000 8080 8090 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "src/main.py"]
"""
    
    # Write Dockerfile
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)
    
    # Build image
    success = run_command("docker build -t npcl/voice-assistant:latest .")
    
    if success:
        print("✅ Docker image built successfully")
    else:
        print("❌ Failed to build Docker image")
    
    return success

def deploy_kubernetes():
    """Deploy to Kubernetes"""
    print("☸️ Deploying to Kubernetes...")
    
    # Check if kubectl is configured
    try:
        run_command("kubectl cluster-info", capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ kubectl is not configured or cluster is not accessible")
        return False
    
    # Apply Kubernetes manifests
    manifests = [
        "kubernetes/namespace.yaml",
        "kubernetes/redis-cluster.yaml",
        "kubernetes/asterisk-deployment.yaml",
        "kubernetes/voice-assistant-deployment.yaml",
        "kubernetes/monitoring.yaml",
        "kubernetes/autoscaling.yaml"
    ]
    
    for manifest in manifests:
        if Path(manifest).exists():
            success = run_command(f"kubectl apply -f {manifest}")
            if not success:
                print(f"❌ Failed to apply {manifest}")
                return False
            print(f"✅ Applied {manifest}")
        else:
            print(f"⚠️ Manifest {manifest} not found, skipping")
    
    print("✅ Kubernetes deployment completed")
    return True

def deploy_docker_compose():
    """Deploy using Docker Compose"""
    print("🐳 Deploying with Docker Compose...")
    
    # Create enhanced docker-compose.yml
    compose_content = {
        "version": "3.8",
        "services": {
            "voice-assistant": {
                "build": ".",
                "image": "npcl/voice-assistant:latest",
                "container_name": "voice-assistant-app",
                "ports": [
                    "8000:8000",
                    "8080:8080",
                    "8090:8090",
                    "9090:9090"
                ],
                "environment": [
                    "SECURITY_ENABLED=true",
                    "METRICS_ENABLED=true",
                    "TRACING_ENABLED=true",
                    "DASHBOARD_ENABLED=true",
                    "CLUSTERING_ENABLED=false",
                    "ARI_BASE_URL=http://asterisk:8088/ari"
                ],
                "env_file": ".env",
                "volumes": [
                    "./sounds:/app/sounds",
                    "./logs:/app/logs"
                ],
                "depends_on": [
                    "asterisk",
                    "redis",
                    "prometheus"
                ],
                "restart": "unless-stopped",
                "networks": ["voice-assistant-net"]
            },
            "asterisk": {
                "image": "andrius/asterisk:18-current",
                "container_name": "voice-assistant-asterisk",
                "ports": [
                    "5060:5060/udp",
                    "8088:8088",
                    "10000-20000:10000-20000/udp"
                ],
                "volumes": [
                    "./asterisk-config:/etc/asterisk:ro",
                    "./sounds:/var/lib/asterisk/sounds/custom",
                    "asterisk-logs:/var/log/asterisk",
                    "asterisk-spool:/var/spool/asterisk"
                ],
                "environment": [
                    "ASTERISK_UID=1000",
                    "ASTERISK_GID=1000"
                ],
                "restart": "unless-stopped",
                "networks": ["voice-assistant-net"]
            },
            "redis": {
                "image": "redis:7-alpine",
                "container_name": "voice-assistant-redis",
                "ports": ["6379:6379"],
                "volumes": ["redis-data:/data"],
                "command": "redis-server --appendonly yes",
                "restart": "unless-stopped",
                "networks": ["voice-assistant-net"]
            },
            "prometheus": {
                "image": "prom/prometheus:latest",
                "container_name": "voice-assistant-prometheus",
                "ports": ["9091:9090"],
                "volumes": [
                    "./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml",
                    "prometheus-data:/prometheus"
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus/",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--web.enable-lifecycle"
                ],
                "restart": "unless-stopped",
                "networks": ["voice-assistant-net"]
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "container_name": "voice-assistant-grafana",
                "ports": ["3000:3000"],
                "environment": [
                    "GF_SECURITY_ADMIN_PASSWORD=admin123"
                ],
                "volumes": [
                    "grafana-data:/var/lib/grafana",
                    "./monitoring/grafana:/etc/grafana/provisioning"
                ],
                "restart": "unless-stopped",
                "networks": ["voice-assistant-net"]
            }
        },
        "volumes": {
            "asterisk-logs": {},
            "asterisk-spool": {},
            "redis-data": {},
            "prometheus-data": {},
            "grafana-data": {}
        },
        "networks": {
            "voice-assistant-net": {
                "driver": "bridge"
            }
        }
    }
    
    # Write docker-compose.yml
    with open("docker-compose.enterprise.yml", "w") as f:
        yaml.dump(compose_content, f, default_flow_style=False)
    
    # Create monitoring configuration
    os.makedirs("monitoring", exist_ok=True)
    
    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "scrape_configs": [
            {
                "job_name": "voice-assistant",
                "static_configs": [
                    {"targets": ["voice-assistant:9090"]}
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "10s"
            },
            {
                "job_name": "redis",
                "static_configs": [
                    {"targets": ["redis:6379"]}
                ]
            }
        ]
    }
    
    with open("monitoring/prometheus.yml", "w") as f:
        yaml.dump(prometheus_config, f, default_flow_style=False)
    
    # Deploy with Docker Compose
    success = run_command("docker-compose -f docker-compose.enterprise.yml up -d")
    
    if success:
        print("✅ Docker Compose deployment completed")
        print("\n🌐 Access URLs:")
        print("  - Voice Assistant API: http://localhost:8000")
        print("  - Dashboard: http://localhost:8080")
        print("  - Metrics: http://localhost:9090")
        print("  - Prometheus: http://localhost:9091")
        print("  - Grafana: http://localhost:3000 (admin/admin123)")
    else:
        print("❌ Docker Compose deployment failed")
    
    return success

def run_tests():
    """Run comprehensive tests"""
    print("🧪 Running tests...")
    
    # Install test dependencies
    run_command("pip install -r requirements-test.txt")
    
    # Run tests
    test_commands = [
        "python -m pytest tests/ -v --tb=short",
        "python -m pytest tests/unit/ -v",
        "python -m pytest tests/integration/ -v",
        "python -m pytest tests/performance/ -v"
    ]
    
    for command in test_commands:
        success = run_command(command)
        if not success:
            print(f"❌ Test failed: {command}")
            return False
    
    print("✅ All tests passed")
    return True

def verify_deployment(deployment_type):
    """Verify deployment is working"""
    print("🔍 Verifying deployment...")
    
    if deployment_type == "kubernetes":
        # Check pod status
        try:
            output = run_command("kubectl get pods -n npcl-voice-assistant", capture_output=True)
            print("Pod status:")
            print(output)
        except:
            print("❌ Failed to get pod status")
            return False
    
    elif deployment_type == "docker-compose":
        # Check container status
        try:
            output = run_command("docker-compose -f docker-compose.enterprise.yml ps", capture_output=True)
            print("Container status:")
            print(output)
        except:
            print("❌ Failed to get container status")
            return False
    
    # Test API endpoints
    print("Testing API endpoints...")
    
    import requests
    import time
    
    # Wait for services to start
    time.sleep(30)
    
    endpoints = [
        ("http://localhost:8000/health", "Health Check"),
        ("http://localhost:8000/ready", "Readiness Check"),
        ("http://localhost:9090/metrics", "Metrics"),
        ("http://localhost:8080", "Dashboard")
    ]
    
    for url, name in endpoints:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
            else:
                print(f"⚠️ {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: Failed - {e}")
    
    print("✅ Deployment verification completed")
    return True

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy NPCL Voice Assistant Enterprise")
    parser.add_argument(
        "--deployment-type", 
        choices=["docker-compose", "kubernetes"], 
        default="docker-compose",
        help="Deployment type"
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-build", action="store_true", help="Skip building Docker image")
    parser.add_argument("--verify", action="store_true", help="Verify deployment after completion")
    
    args = parser.parse_args()
    
    print("🚀 NPCL Voice Assistant Enterprise Deployment")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Run tests
    if not args.skip_tests:
        if not run_tests():
            print("❌ Tests failed. Use --skip-tests to deploy anyway.")
            sys.exit(1)
    
    # Build Docker image
    if not args.skip_build:
        if not build_docker_image():
            sys.exit(1)
    
    # Deploy
    if args.deployment_type == "kubernetes":
        success = deploy_kubernetes()
    else:
        success = deploy_docker_compose()
    
    if not success:
        print("❌ Deployment failed")
        sys.exit(1)
    
    # Verify deployment
    if args.verify:
        verify_deployment(args.deployment_type)
    
    print("\n🎉 Enterprise deployment completed successfully!")
    print("\n📋 Next steps:")
    print("1. Configure your SIP phone to connect to the Asterisk server")
    print("2. Call extension 1000 to test the voice assistant")
    print("3. Monitor the system using the dashboard and metrics")
    print("4. Check logs for any issues")
    
    if args.deployment_type == "docker-compose":
        print("\n🛠️ Management commands:")
        print("  - Stop: docker-compose -f docker-compose.enterprise.yml down")
        print("  - Logs: docker-compose -f docker-compose.enterprise.yml logs -f")
        print("  - Restart: docker-compose -f docker-compose.enterprise.yml restart")

if __name__ == "__main__":
    main()