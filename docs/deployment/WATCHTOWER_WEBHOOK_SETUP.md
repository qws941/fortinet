# Watchtower Webhook Setup Guide

This guide explains how to set up Watchtower webhook for automated Docker container updates in the CI/CD pipeline.

## Prerequisites

- Watchtower running with HTTP API enabled
- GitHub repository with Actions enabled
- Access to GitHub repository secrets

## 1. Watchtower Configuration

Ensure Watchtower is running with the HTTP API enabled:

```yaml
# docker-compose.yml
watchtower:
  image: containrrr/watchtower
  container_name: watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  environment:
    - WATCHTOWER_HTTP_API_UPDATE=true
    - WATCHTOWER_HTTP_API_TOKEN=MySuperSecretToken12345
    - WATCHTOWER_POLL_INTERVAL=30
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_INCLUDE_STOPPED=false
    - WATCHTOWER_INCLUDE_RESTARTING=true
  ports:
    - "8080:8080"
  command: --interval 30
```

## 2. Nginx Reverse Proxy Configuration

Configure Nginx to proxy Watchtower API:

```nginx
server {
    listen 443 ssl http2;
    server_name watchtower.jclee.me;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /v1/update {
        proxy_pass http://localhost:8080/v1/update;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 3. GitHub Secrets Setup

Add the following secret to your GitHub repository:

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add:
   - Name: `WATCHTOWER_TOKEN`
   - Value: `MySuperSecretToken12345` (use your actual token)

## 4. CI/CD Pipeline Integration

The GitHub Actions workflow now includes a deploy job that:

1. **Triggers Watchtower Update**: Sends a POST request to the webhook
2. **Waits for Deployment**: Gives time for container update
3. **Health Check**: Verifies the deployment was successful
4. **Version Verification**: Checks if the correct version is deployed

### Workflow Steps:

```yaml
deploy:
  name: 🚀 Deploy to Production
  runs-on: ubuntu-latest
  needs: build
  if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
  
  steps:
  - name: 🔔 Trigger Watchtower Update
    run: |
      curl -X POST https://watchtower.jclee.me/v1/update \
        -H "Authorization: Bearer ${{ secrets.WATCHTOWER_TOKEN }}"
```

## 5. Testing the Webhook

Test the webhook manually:

```bash
# Test from command line
curl -X POST https://watchtower.jclee.me/v1/update \
  -H "Authorization: Bearer MySuperSecretToken12345" \
  -H "Content-Type: application/json"

# Expected response: 204 No Content or 200 OK
```

## 6. Monitoring

The deployment job includes:

- **Retry Logic**: Health check retries up to 10 times
- **Version Verification**: Ensures the deployed version matches the commit SHA
- **Deployment Summary**: Shows deployment details regardless of success/failure

## 7. Security Considerations

1. **Use Strong Tokens**: Generate a secure random token
   ```bash
   openssl rand -base64 32
   ```

2. **HTTPS Only**: Always use HTTPS for the webhook endpoint

3. **IP Whitelisting**: Consider restricting access to GitHub Actions IP ranges

4. **Token Rotation**: Regularly rotate the webhook token

## 8. Troubleshooting

### Webhook Returns 401 Unauthorized
- Check if the token in GitHub secrets matches Watchtower configuration
- Verify the Authorization header format

### Deployment Not Updating
- Check Watchtower logs: `docker logs watchtower`
- Ensure the container has the correct labels
- Verify registry credentials are configured

### Health Check Fails
- Check if the application started correctly
- Verify the health endpoint is accessible
- Check application logs: `docker logs fortinet`

## 9. Alternative Update Methods

If webhook is not available, you can use:

1. **SSH Deploy**:
   ```yaml
   - name: Deploy via SSH
     run: |
       ssh user@server "docker pull registry.jclee.me/fortinet:latest && docker restart fortinet"
   ```

2. **Docker Remote API**:
   ```yaml
   - name: Deploy via Docker API
     run: |
       curl -X POST http://server:2375/containers/fortinet/restart
   ```

## 10. Complete Deployment Flow

1. Developer pushes code to main/master branch
2. GitHub Actions builds and tests the code
3. Docker image is built and pushed to registry.jclee.me
4. Webhook triggers Watchtower update
5. Watchtower pulls the new image and updates containers
6. Health check verifies successful deployment
7. Deployment summary is generated

This automated flow ensures zero-downtime deployments with proper verification.