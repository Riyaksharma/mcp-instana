# Docker Guide for MCP Instana

This document provides detailed instructions for building, running, and deploying Docker containers for the MCP Instana server.

## Building Docker Images

### Basic Build

```bash
# Build a local image
docker build -t mcp-instana .
```

### Multi-Architecture Build

The MCP Instana Docker image supports multiple processor architectures, making it portable across different environments.

#### Supported Architectures
- ✅ **amd64/x86_64**: Standard Intel/AMD processors (Windows, Linux, most cloud VMs)
- ✅ **arm64/aarch64**: Apple Silicon (M1/M2/M3), AWS Graviton, Raspberry Pi 4, etc.

#### Building Multi-Architecture Images

```bash
# Set up Docker BuildKit builder if you haven't already
docker buildx create --name multiarch --driver docker-container --use

# Build and push a multi-architecture image to a registry
docker buildx build --platform linux/amd64,linux/arm64 -t username/mcp-instana:latest --push .
```

#### Using the Helper Script

```bash
# Make the script executable
chmod +x build_multiarch.sh

# Build for local architecture
./build_multiarch.sh

# Build and push multi-architecture image
./build_multiarch.sh --registry username/ --push
```

#### What the Build Does
1. **Multi-stage build** for optimal size and security
2. **Builder stage**: Installs only runtime dependencies from `pyproject-runtime.toml`
3. **Runtime stage**: Creates minimal production image with non-root user
4. **Security**: No hardcoded secrets, proper user permissions
5. **Optimization**: Only essential dependencies (20 vs 95+ in development)

#### Benefits of Multi-Architecture Images
- **Cross-Platform Compatibility**: Run the same image on any supported architecture
- **Seamless Deployment**: No need to build different images for different environments
- **CI/CD Simplification**: Build once, deploy anywhere
- **Cloud Flexibility**: Switch between cloud providers and instance types without rebuilding images

#### How It Works
1. The multi-architecture image is a "manifest list" containing images for each architecture
2. When you pull the image, Docker automatically selects the correct architecture for your system
3. The image runs natively on your architecture without emulation, ensuring optimal performance

## Running the Docker Container

### Basic Usage
```bash
# Run the container (no credentials needed in the container)
docker run -p 8080:8080 mcp-instana

# Run with custom port
docker run -p 8081:8080 mcp-instana
```

### Docker Compose Example
```yaml
version: '3.8'
services:
  mcp-instana:
    build: .
    ports:
      - "8080:8080"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://127.0.0.1:8080/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Docker Security Features

### Security Best Practices Implemented
- ✅ **Non-root user**: Container runs as `mcpuser` (not root)
- ✅ **No secrets in container**: Credentials are passed via HTTP headers from clients, not stored in the container
- ✅ **Minimal dependencies**: Only 20 essential runtime dependencies
- ✅ **Multi-stage build**: Build tools don't make it to final image
- ✅ **Health checks**: Built-in container health monitoring
- ✅ **Optimized base image**: Uses `python:3.11-slim`
- ✅ **Multi-architecture support**: Run natively on any supported platform

### Image Size Optimization
- **Original approach**: 95+ dependencies → ~1-2GB+ image
- **Optimized approach**: 20 dependencies → ~266MB image
- **Size reduction**: ~70-80% smaller images
- **Benefits**: Faster deployments, lower storage costs, reduced attack surface

## Testing the Docker Container

### Health Check
```bash
# Check if container is healthy
docker ps

# Test the MCP endpoint
curl http://localhost:8080/mcp/
```

### MCP Inspector Testing
```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8080/mcp/
```

### Logs and Debugging
```bash
# View container logs
docker logs <container_id>

# Follow logs in real-time
docker logs -f <container_id>

# Execute commands in running container
docker exec -it <container_id> /bin/bash
```

## Production Deployment

### Recommended Production Setup
1. **Run container without credentials** - The container runs in Streamable HTTP mode, so no Instana credentials are needed in the container
2. **Configure clients with credentials** - Pass Instana credentials via HTTP headers from MCP clients (Claude Desktop, GitHub Copilot, etc.)
3. **Set up proper logging** and monitoring
4. **Configure health checks** for container orchestration
5. **Use container orchestration** (Kubernetes, Docker Swarm, etc.)
6. **Implement proper backup** and disaster recovery

### Kubernetes Example
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-instana
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-instana
  template:
    metadata:
      labels:
        app: mcp-instana
    spec:
      containers:
      - name: mcp-instana
        image: mcp-instana:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Troubleshooting Docker Issues

### Container Won't Start
```bash
# Check container logs
docker logs <container_id>

# Common issues:
# 1. Port already in use
# 2. Invalid container image
# 3. Missing dependencies

# Credentials are passed via HTTP headers from the MCP client
```

### Connection Issues
```bash
# Test container connectivity
docker exec -it <container_id> curl http://127.0.0.1:8080/health

# Check port mapping
docker port <container_id>
```

### Performance Issues
```bash
# Check container resource usage
docker stats <container_id>

# Monitor container health
docker inspect <container_id> | grep -A 10 Health
```
