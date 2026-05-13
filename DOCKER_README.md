# Pramana RAG Docker Guide

Complete guide to containerizing, running, and publishing the Pramana RAG service on Docker and Docker Hub.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Building the Docker Image](#building-the-docker-image)
4. [Running with Docker Compose](#running-with-docker-compose)
5. [Running with Docker CLI](#running-with-docker-cli)
6. [Volume Management](#volume-management)
7. [Environment Variables](#environment-variables)
8. [Using the Service](#using-the-service)
9. [Publishing to Docker Hub](#publishing-to-docker-hub)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

**For the impatient (5 minutes):**

```bash
# 1. Clone and navigate to repo
cd PowerMind

# 2. Create environment file
cp .env.example .env.docker
# Edit .env.docker and add your NVIDIA_KEY

# 3. Build image
docker build -f Dockerfile.service -t pramana-rag:1.0.0 .

# 4. Run using docker-compose
docker-compose -f docker-compose.service.yml up

# 5. In another terminal, run a query
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ask "What is this document about?"

# 6. Stop
docker-compose -f docker-compose.service.yml down
```

---

## Architecture Overview

### What's in the Docker Image

```
✅ INCLUDED in Image:
  - Python 3.12 runtime
  - All Python dependencies (faiss, transformers optional, API clients)
  - Pramana RAG source code
  - System libraries for PDF processing
  - ~500 MB compressed image

❌ NOT in Image (Mounted as Volumes):
  - Model files (Qwen, Qwen_VL, E5_Small) - too large
  - Input PDFs (service/data/) - user-provided
  - Ingested data (service/storage/) - generated at runtime
  - API keys (secrets) - passed at runtime via environment
```

### Volume Mounts

| Mount Path | Host Path | Purpose | Required | Writable |
|---|---|---|---|---|
| `/app/service/storage` | `./service/storage` | Ingested documents, indexes, embeddings | Yes | Yes |
| `/app/service/data` | `./service/data` | Input PDFs for ingestion | Yes | No (read-only) |
| `/app/models/Qwen` | `./Qwen` | Local Qwen model (optional) | No | No |
| `/app/models/Qwen_VL` | `./Qwen_VL` | Local Qwen-VL model (optional) | No | No |
| `/app/models/E5_Small` | `./E5_Small` | Local E5 embeddings model (legacy) | No | No |

---

## Building the Docker Image

### Build Command

```bash
# Build with default tag
docker build -f Dockerfile.service -t pramana-rag:1.0.0 .

# Or build with multiple tags
docker build -f Dockerfile.service \
  -t pramana-rag:1.0.0 \
  -t pramana-rag:latest \
  .
```

### Build Output

```
Step 1/20 : FROM python:3.12-slim as builder
Step 2/20 : WORKDIR /build
...
Step 20/20 : CMD ["python", "-m", "powermind_rag.cli", "--help"]
Successfully built abc123def456
Successfully tagged pramana-rag:1.0.0
Successfully tagged pramana-rag:latest
```

### Verify Build

```bash
# List images
docker images | grep pramana-rag

# Output should show ~500-600MB (depending on dependencies)
REPOSITORY     TAG      IMAGE ID       CREATED         SIZE
pramana-rag    1.0.0    abc123def456   2 minutes ago    562MB
pramana-rag    latest   abc123def456   2 minutes ago    562MB
```

### Build Cache

The Dockerfile uses multi-stage builds to maximize layer caching:

- **Stage 1 (Builder):** Installs dependencies into a virtual environment
  - This layer is cached if dependencies don't change
  - Subsequent builds are fast (~30 seconds) if code changes only

- **Stage 2 (Runtime):** Copies venv from stage 1, adds application code
  - Code changes don't trigger dependency reinstall
  - Result: lightweight final image without build tools

---

## Running with Docker Compose

**Recommended for local development and testing**

### Setup

1. **Create environment file:**

```bash
cp .env.example .env.docker
```

2. **Edit `.env.docker`** and add your API keys:

```bash
# Linux/Mac
nano .env.docker

# Windows (PowerShell)
notepad .env.docker
```

Minimum required keys:

```env
NVIDIA_KEY="<your-nvidia-api-key>"
GEMINI_API_KEY_1="<your-gemini-api-key>"
MISTRAL_API_KEY="<your-mistral-api-key>"
```

See `.env.example` for all available options.

3. **Build the image:**

```bash
docker build -f Dockerfile.service -t pramana-rag:1.0.0 .
```

### Start Services

```bash
# Start in foreground (see logs)
docker-compose -f docker-compose.service.yml up

# Or start in background
docker-compose -f docker-compose.service.yml up -d

# View logs
docker-compose -f docker-compose.service.yml logs -f service
```

### Run CLI Commands

```bash
# Show help
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli --help

# Ingest a PDF
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ingest "/app/service/data/sample.pdf"

# Ask a question
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ask "What are the key financial metrics?"

# Run batch test questions
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ask-batch

# Ingest entire directory
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ingest-dir "/app/service/data"
```

### Stop Services

```bash
# Stop containers (data persists)
docker-compose -f docker-compose.service.yml stop

# Stop and remove containers
docker-compose -f docker-compose.service.yml down

# Stop and remove everything including volumes
docker-compose -f docker-compose.service.yml down -v
```

---

## Running with Docker CLI

**For manual control and scripting**

### Basic Run

```bash
docker run \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  -v $(pwd)/service/data:/app/service/data \
  pramana-rag:1.0.0 \
  python -m powermind_rag.cli ask "question"
```

### With Individual Environment Variables

```bash
docker run \
  -e NVIDIA_KEY="your-key" \
  -e GEMINI_API_KEY_1="your-key" \
  -e POWERMIND_STORAGE_DIR="/app/service/storage" \
  -v $(pwd)/service/storage:/app/service/storage \
  -v $(pwd)/service/data:/app/service/data \
  pramana-rag:1.0.0 \
  python -m powermind_rag.cli ask "question"
```

### Windows PowerShell (Paths with backslashes)

```powershell
docker run `
  --env-file .env.docker `
  -v "${PWD}\service\storage:/app/service/storage" `
  -v "${PWD}\service\data:/app/service/data" `
  pramana-rag:1.0.0 `
  python -m powermind_rag.cli ask "question"
```

### Windows Command Prompt (cmd.exe)

```cmd
docker run ^
  --env-file .env.docker ^
  -v %CD%\service\storage:/app/service/storage ^
  -v %CD%\service\data:/app/service/data ^
  pramana-rag:1.0.0 ^
  python -m powermind_rag.cli ask "question"
```

### Run in Interactive Mode (Bash)

```bash
docker run -it \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  -v $(pwd)/service/data:/app/service/data \
  pramana-rag:1.0.0 \
  /bin/bash

# Now inside container:
python -m powermind_rag.cli ask "question"
exit
```

### Run MCP Server

```bash
docker run -d \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  -p 8765:8765 \
  --name pramana-mcp \
  pramana-rag:1.0.0 \
  python -m powermind_rag.mcp_server

# View logs
docker logs -f pramana-mcp

# Stop
docker stop pramana-mcp
```

### Named Container (Reuse)

```bash
# Create container once
docker create \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  -v $(pwd)/service/data:/app/service/data \
  --name pramana-work \
  pramana-rag:1.0.0

# Run commands
docker start pramana-work
docker exec pramana-work python -m powermind_rag.cli ask "question"

# Stop when done
docker stop pramana-work

# Remove
docker rm pramana-work
```

---

## Volume Management

### Understanding Volumes

Volumes persist data outside the container and allow host ↔ container file sharing.

### Bind Mounts (Recommended for Development)

Uses host directories directly:

```bash
-v /absolute/host/path:/container/path
```

Example:

```bash
docker run -v $(pwd)/service/storage:/app/service/storage ...
```

**Pros:** Direct access to files, version control friendly
**Cons:** Permissions issues on Linux/Mac, path differences across OS

### Named Volumes (Recommended for Production)

Docker-managed volumes:

```bash
# Create volume
docker volume create pramana-storage

# Use volume
docker run -v pramana-storage:/app/service/storage ...
```

**Pros:** Better performance, automatic backups, cross-platform
**Cons:** Less accessible from host

### Inspect Volume Usage

```bash
# List all volumes
docker volume ls

# Inspect specific volume
docker volume inspect pramana-storage

# Copy from volume to host
docker run --rm -v pramana-storage:/data -v $(pwd):/host \
  busybox cp -r /data /host/backup

# Remove volume
docker volume rm pramana-storage
```

### Read-Only Volumes

For input data, use `:ro` flag:

```bash
-v $(pwd)/service/data:/app/service/data:ro
```

This prevents accidental modifications.

---

## Environment Variables

### Minimal Setup (API-Only)

```env
# Required: NVIDIA embeddings
NVIDIA_KEY="<your-key>"
POWERMIND_STORAGE_DIR="/app/service/storage"
POWERMIND_DEVICE="api"
```

### Recommended Setup (Full Features)

```env
# Core
NVIDIA_KEY="<your-key>"
GEMINI_API_KEY_1="<your-key>"
MISTRAL_API_KEY="<your-key>"

# Configuration
POWERMIND_STORAGE_DIR="/app/service/storage"
POWERMIND_DEVICE="api"
POWERMIND_RELEVANCE_PROVIDER="gemini"
POWERMIND_ENABLE_VISUAL_UNDERSTANDING="true"

# Generation
POWERMIND_GENERATION_PROVIDER="nvidia"
POWERMIND_ENABLE_QUERY_VLM_FALLBACK="1"
```

### All Options

See `.env.example` for complete reference with descriptions.

### Runtime Override

Environment variables passed at runtime override `.env.docker`:

```bash
docker run \
  --env-file .env.docker \
  -e POWERMIND_DEVICE="cuda" \  # Overrides .env.docker
  pramana-rag:1.0.0 ...
```

---

## Using the Service

### CLI Commands

#### Help

```bash
docker run ... python -m powermind_rag.cli --help
```

#### Ingest Single Document

```bash
docker run ... python -m powermind_rag.cli ingest "/app/service/data/report.pdf"
```

**Output:** Prints progress, saves to `/app/service/storage/{document_id}/text_records.json`

#### Ingest Directory

```bash
docker run ... python -m powermind_rag.cli ingest-dir "/app/service/data"
```

**Output:** Processes all PDFs, saves each to separate storage directories

#### Ask Question

```bash
docker run ... python -m powermind_rag.cli ask "What is the revenue?"
```

**Output:** Shows answer with citations and timing breakdown

#### Ask Batch (7 Test Questions)

```bash
docker run ... python -m powermind_rag.cli ask-batch
```

**Output:** Runs predefined test questions, displays all results

### MCP Server

Start MCP server for LLM/Claude integration:

```bash
docker run -d \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  pramana-rag:1.0.0 \
  python -m powermind_rag.mcp_server
```

Configuration via MCP:

1. Call `configure_environment` tool
2. Set environment variables
3. Call `environment_status` to verify

### Python API

If you need programmatic access:

```python
from powermind_rag.pipeline import MultimodalRAGPipeline
from powermind_rag.config import RAGConfig

# Load config from environment
config = RAGConfig.from_env()

# Create pipeline
pipeline = MultimodalRAGPipeline(config)

# Ingest
pipeline.ingest_document("path/to.pdf")

# Query
answer = pipeline.answer("question")
print(answer)
```

---

## Publishing to Docker Hub

### Prerequisites

1. **Docker Hub Account** (free)
   - Sign up: https://hub.docker.com/
   - Note your username (e.g., `johndoe`)

2. **Docker installed locally**
   ```bash
   docker --version
   ```

### Step 1: Login to Docker Hub

```bash
docker login
```

When prompted:
```
Username: <your-docker-hub-username>
Password: <your-docker-hub-password>
Login Succeeded
```

### Step 2: Tag Image

Tag your local image with Docker Hub registry:

```bash
# Format: docker tag <local-image>:<tag> <username>/<repo>:<tag>
docker tag pramana-rag:1.0.0 johndoe/pramana-rag:1.0.0
docker tag pramana-rag:1.0.0 johndoe/pramana-rag:latest
```

Verify tags:

```bash
docker images | grep pramana-rag

# Output:
REPOSITORY                    TAG      IMAGE ID       CREATED         SIZE
johndoe/pramana-rag          latest   abc123def456   5 minutes ago    562MB
johndoe/pramana-rag          1.0.0    abc123def456   5 minutes ago    562MB
pramana-rag                  1.0.0    abc123def456   5 minutes ago    562MB
```

### Step 3: Push to Docker Hub

```bash
# Push all tags
docker push johndoe/pramana-rag:1.0.0
docker push johndoe/pramana-rag:latest

# Or push repository (all tags)
docker push johndoe/pramana-rag
```

**Output:**

```
The push refers to a repository [docker.io/johndoe/pramana-rag]
d3faecf05d88: Pushed
a4d3c1d47a7f: Pushed
...
1.0.0: digest: sha256:abc123... size: 5678
latest: digest: sha256:abc123... size: 5678
```

### Step 4: Verify on Docker Hub

1. Go to https://hub.docker.com/r/johndoe/pramana-rag
2. Verify tags are visible
3. Copy pull command

### Step 5: Pull on Another System

```bash
docker pull johndoe/pramana-rag:1.0.0

docker run \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  johndoe/pramana-rag:1.0.0 \
  python -m powermind_rag.cli ask "question"
```

**✅ Success!** Image works identically on any system with Docker.

---

### Versioning Strategy

Recommend semantic versioning:

| Tag | Purpose | When to push |
|---|---|---|
| `1.0.0` | Stable release | After testing, for production |
| `1.0` | Latest patch of 1.0 | Automatic with 1.0.0 |
| `1` | Latest of major version 1 | Automatic with 1.0.0 |
| `latest` | Latest of everything | After 1.0.0, 1.1.0, etc. |
| `dev` (optional) | Development builds | For CI/CD |

Example workflow:

```bash
# Development build
docker build -t pramana-rag:dev -f Dockerfile.service .
docker tag pramana-rag:dev johndoe/pramana-rag:dev
docker push johndoe/pramana-rag:dev

# Release 1.0.0
docker build -t pramana-rag:1.0.0 -f Dockerfile.service .
docker tag pramana-rag:1.0.0 johndoe/pramana-rag:1.0.0
docker tag pramana-rag:1.0.0 johndoe/pramana-rag:1.0
docker tag pramana-rag:1.0.0 johndoe/pramana-rag:1
docker tag pramana-rag:1.0.0 johndoe/pramana-rag:latest
docker push johndoe/pramana-rag:1.0.0
docker push johndoe/pramana-rag:1.0
docker push johndoe/pramana-rag:1
docker push johndoe/pramana-rag:latest
```

---

### Create README on Docker Hub

1. Go to https://hub.docker.com/r/johndoe/pramana-rag
2. Click "Edit repository"
3. Paste Docker Hub description:

```markdown
# Pramana RAG - Production-Grade Multimodal RAG

Production API-first multimodal RAG system with NVIDIA embeddings, Mistral OCR, 
Gemini/NVIDIA VLM, hybrid retrieval, RRF, and CRAG.

## Quick Start

\`\`\`bash
docker run \
  -e NVIDIA_KEY="your-key" \
  -v $(pwd)/service/storage:/app/service/storage \
  johndoe/pramana-rag:latest \
  python -m powermind_rag.cli ask "What is this about?"
\`\`\`

## Documentation

See the full guide: https://github.com/yourusername/PowerMind/blob/main/DOCKER_README.md

## Features

- ✅ API-first (no GPU required by default)
- ✅ NVIDIA embeddings for dense retrieval
- ✅ Hybrid search (BM25 + dense + keyword + RRF)
- ✅ Gemini relevance grading (CRAG)
- ✅ Visual page understanding (VLM)
- ✅ MCP server support
- ✅ Multi-turn ingestion with OCR

## License

[Your License]
```

---

### Optional: Setup CI/CD (GitHub Actions)

Auto-build on new releases:

```yaml
# .github/workflows/docker-publish.yml
name: Docker Build & Push

on:
  push:
    tags:
      - 'v*'

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: docker/setup-buildx-action@v2
      
      - uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - uses: docker/build-push-action@v4
        with:
          file: ./Dockerfile.service
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/pramana-rag:latest
            ${{ secrets.DOCKER_USERNAME }}/pramana-rag:${{ github.ref_name }}
```

---

## Troubleshooting

### Issue: Image too large (> 1GB)

**Cause:** Model files included in image or not cleaned

**Fix:**

```bash
# Verify .dockerignore exists and has model exclusions
cat .dockerignore | grep -E "Qwen|E5_Small"

# Rebuild
docker build -f Dockerfile.service -t pramana-rag:1.0.0 --no-cache .

# Check size
docker images pramana-rag
```

Expected: ~500-600 MB

### Issue: "Module not found" errors

**Cause:** Python dependencies not installed or wrong Python path

**Fix:**

```bash
# Verify image was built successfully
docker build -f Dockerfile.service --no-cache -t pramana-rag:test .

# Test with help command
docker run pramana-rag:test python -m powermind_rag.cli --help

# If fails, check build output for errors
```

### Issue: "Permission denied" on mounted volumes (Linux/Mac)

**Cause:** Docker container running as different user than host

**Fix:**

```bash
# Run as current user
docker run \
  --user $(id -u):$(id -g) \
  -v $(pwd)/service/storage:/app/service/storage \
  pramana-rag:1.0.0 ...
```

### Issue: Storage/data volumes not syncing

**Cause:** Using wrong mount paths or host path doesn't exist

**Fix:**

```bash
# Verify host paths exist
ls -la service/storage
ls -la service/data

# Use absolute paths (better)
docker run -v $(pwd)/service/storage:/app/service/storage ...

# Or inspect volume
docker volume inspect pramana-storage
```

### Issue: API keys not recognized

**Cause:** `.env.docker` not loaded or malformed

**Fix:**

```bash
# Verify .env.docker exists
ls -la .env.docker

# Check for syntax errors (no spaces around =)
cat .env.docker | grep NVIDIA_KEY

# Output should show: NVIDIA_KEY="your-key"
# NOT: NVIDIA_KEY = "your-key" (spaces will break it)

# Or pass directly
docker run -e NVIDIA_KEY="your-actual-key" ...
```

### Issue: Docker Compose networking error

**Cause:** Port conflicts or network issues

**Fix:**

```bash
# Check existing networks
docker network ls

# Remove conflicting compose project
docker-compose -f docker-compose.service.yml down -v

# Rebuild
docker-compose -f docker-compose.service.yml up --build
```

### Issue: Out of memory or container killed

**Cause:** Insufficient system resources

**Fix:**

```bash
# Increase Docker resources (Desktop settings)
# Or use resource limits in docker-compose.yml:

# deploy:
#   resources:
#     limits:
#       memory: 8G
#     reservations:
#       memory: 4G

# Reduce payload or batch size
docker run ... python -m powermind_rag.cli ingest "/app/service/data/small.pdf"
```

---

## Summary

| Task | Command |
|---|---|
| **Build** | `docker build -f Dockerfile.service -t pramana-rag:1.0.0 .` |
| **Run (compose)** | `docker-compose -f docker-compose.service.yml up` |
| **Run (CLI)** | `docker run --env-file .env.docker -v ... pramana-rag:1.0.0 python -m powermind_rag.cli ask "q"` |
| **Push to Docker Hub** | `docker login && docker tag pramana-rag:1.0.0 user/pramana-rag:1.0.0 && docker push user/pramana-rag:1.0.0` |
| **Pull from Docker Hub** | `docker pull user/pramana-rag:1.0.0` |

---

**Happy containerizing! 🐳**
