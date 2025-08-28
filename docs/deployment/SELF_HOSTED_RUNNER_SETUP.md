# Self-Hosted GitHub Actions Runner Setup Guide

This guide explains how to set up a self-hosted GitHub Actions runner for the FortiGate Nextrade project to bypass GitHub Actions billing limitations.

## Overview

Self-hosted runners allow you to run GitHub Actions workflows on your own infrastructure, eliminating usage costs while maintaining full control over the execution environment.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker installed on the host
- Sufficient disk space for builds (minimum 20GB)
- Network access to GitHub and Docker registries

## Installation Steps

### 1. Create Runner Directory

```bash
# Create dedicated user for runner
sudo useradd -m -s /bin/bash github-runner
sudo usermod -aG docker github-runner

# Create runner directory
sudo mkdir -p /opt/github-runner
sudo chown github-runner:github-runner /opt/github-runner
```

### 2. Download and Configure Runner

```bash
# Switch to runner user
sudo su - github-runner
cd /opt/github-runner

# Download latest runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure runner
./config.sh --url https://github.com/YOUR_ORG/fortinet \
  --token YOUR_RUNNER_TOKEN \
  --name "self-hosted-01" \
  --labels "self-hosted,linux,x64,docker" \
  --work "_work"
```

### 3. Install Dependencies

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  curl \
  wget \
  git \
  python3.11 \
  python3-pip \
  docker.io \
  docker-compose

# Ensure Docker permissions
sudo usermod -aG docker github-runner
```

### 4. Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/github-runner.service > /dev/null <<EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=github-runner
WorkingDirectory=/opt/github-runner
ExecStart=/opt/github-runner/run.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=github-runner
Environment="DOCKER_HOST=unix:///var/run/docker.sock"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable github-runner
sudo systemctl start github-runner
sudo systemctl status github-runner
```

### 5. Configure Docker Access

```bash
# Ensure runner can access Docker
sudo chmod 666 /var/run/docker.sock

# Add Docker credentials for registry access
docker login registry.jclee.me -u YOUR_USERNAME -p YOUR_PASSWORD
```

## Monitoring and Maintenance

### Check Runner Status

```bash
# View service logs
sudo journalctl -u github-runner -f

# Check runner status
sudo systemctl status github-runner

# View running jobs
docker ps
```

### Update Runner

```bash
# Stop service
sudo systemctl stop github-runner

# Download new version
cd /opt/github-runner
sudo su - github-runner
./config.sh remove --token YOUR_REMOVAL_TOKEN
# Download and extract new version
# Reconfigure with ./config.sh

# Start service
sudo systemctl start github-runner
```

## Security Considerations

1. **Dedicated User**: Always run the runner as a non-root user
2. **Network Isolation**: Consider using a dedicated network segment
3. **Resource Limits**: Set CPU and memory limits if needed
4. **Regular Updates**: Keep the runner software updated
5. **Secrets Management**: Never store secrets on the runner host

## Troubleshooting

### Runner Not Appearing in GitHub

1. Check the configuration token is valid
2. Verify network connectivity to GitHub
3. Check service logs for errors

### Docker Permission Issues

```bash
# Fix Docker socket permissions
sudo chmod 666 /var/run/docker.sock

# Verify Docker access
sudo -u github-runner docker info
```

### Build Failures

1. Check disk space: `df -h`
2. Verify Docker daemon: `sudo systemctl status docker`
3. Check runner logs: `sudo journalctl -u github-runner -n 100`

## Performance Optimization

### Docker Build Cache

```bash
# Configure Docker to use buildkit
echo '{"features":{"buildkit":true}}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

### Concurrent Jobs

```bash
# Configure multiple runners for parallel jobs
# Repeat installation with different names:
./config.sh --name "self-hosted-02" --labels "self-hosted,linux,x64,docker"
```

## Cost Savings

By using self-hosted runners, you save:
- No per-minute charges for GitHub Actions
- Full control over build environment
- Faster builds with local caching
- No usage limits

## Next Steps

1. Monitor the first few workflow runs
2. Adjust runner resources based on usage
3. Consider adding more runners for parallelism
4. Set up runner auto-scaling if needed

## References

- [GitHub Self-Hosted Runners Documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Runner Security Best Practices](https://docs.github.com/en/actions/hosting-your-own-runners/about-self-hosted-runners#self-hosted-runner-security)