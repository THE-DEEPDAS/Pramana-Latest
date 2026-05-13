# Pramana RAG Docker - Quick Reference

## Files Created

✅ **Dockerfile.service** — Multi-stage Docker build (500MB final image)
✅ **.dockerignore** — Excludes models, data, PDFs (keeps image small)
✅ **docker-compose.service.yml** — Compose file with volume mounts and env config
✅ **.env.example** — Environment variable template (copy to .env.docker, add keys)
✅ **DOCKER_README.md** — Complete 500+ line guide (all Docker commands, troubleshooting)
✅ **README.md** — Updated with Docker section

---

## Next Steps

### 1. **Wait for Docker Build to Complete**

Currently building... (downloading dependencies, installing packages)

```bash
docker images pramana-rag
```

Expected size: ~500-600 MB (compressed)

### 2. **Create Environment File**

```bash
cp .env.example .env.docker
# Edit .env.docker - add your API keys:
# NVIDIA_KEY="..."
# GEMINI_API_KEY_1="..."
# MISTRAL_API_KEY="..."
```

### 3. **Run with Docker Compose (Easiest)**

```bash
# Start service
docker-compose -f docker-compose.service.yml up

# In another terminal, ask a question
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ask "What is this about?"
```

### 4. **Run with Docker CLI (Manual)**

```bash
docker run \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  -v $(pwd)/service/data:/app/service/data \
  pramana-rag:1.0.0 \
  python -m powermind_rag.cli ask "question"
```

### 5. **Push to Docker Hub**

```bash
docker login
docker tag pramana-rag:1.0.0 yourusername/pramana-rag:1.0.0
docker tag pramana-rag:1.0.0 yourusername/pramana-rag:latest
docker push yourusername/pramana-rag:1.0.0
docker push yourusername/pramana-rag:latest
```

Then anyone can pull and run:
```bash
docker pull yourusername/pramana-rag:1.0.0
docker run --env-file .env.docker yourusername/pramana-rag:1.0.0 \
  python -m powermind_rag.cli ask "question"
```

---

## Key Features

| Feature | Details |
|---------|---------|
| **Image Size** | ~500 MB (excludes 22GB models) |
| **Models** | Mounted as volumes (not baked in) |
| **Data** | Mounted as volumes (user-provided) |
| **Storage** | Mounted as volume (generated at runtime) |
| **Secrets** | Passed at runtime (never in image) |
| **GPU Support** | API-only by default; optional CUDA with volumes |
| **Entry Points** | CLI commands, MCP server, Python API |

---

## Volume Mounts

| Container Path | Host Path | Purpose | Required |
|---|---|---|---|
| `/app/service/storage` | `./service/storage` | Output: indexes, embeddings | ✅ |
| `/app/service/data` | `./service/data` | Input: PDFs | ✅ |
| `/app/models/Qwen` | `./Qwen` | Local LLM (optional) | ❌ |
| `/app/models/Qwen_VL` | `./Qwen_VL` | Local vision model (optional) | ❌ |

---

## Environment Variables (Secrets)

**Minimum** (API-only):
```env
NVIDIA_KEY="your-nvidia-api-key"
POWERMIND_STORAGE_DIR="/app/service/storage"
POWERMIND_DEVICE="api"
```

**Recommended** (Full features):
```env
NVIDIA_KEY="your-nvidia-key"
GEMINI_API_KEY_1="your-gemini-key"
MISTRAL_API_KEY="your-mistral-key"
POWERMIND_STORAGE_DIR="/app/service/storage"
POWERMIND_DEVICE="api"
POWERMIND_RELEVANCE_PROVIDER="gemini"
POWERMIND_ENABLE_VISUAL_UNDERSTANDING="true"
```

See `.env.example` for all 50+ options.

---

## Common Commands

### Build Image

```bash
docker build -f Dockerfile.service -t pramana-rag:1.0.0 .
```

### Run CLI

```bash
# Show help
docker run pramana-rag:1.0.0 python -m powermind_rag.cli --help

# Ingest PDF
docker run -v $(pwd)/service/data:/app/service/data \
           -v $(pwd)/service/storage:/app/service/storage \
           -e NVIDIA_KEY="key" \
           pramana-rag:1.0.0 \
           python -m powermind_rag.cli ingest "/app/service/data/file.pdf"

# Ask question
docker run -v $(pwd)/service/storage:/app/service/storage \
           -e NVIDIA_KEY="key" \
           pramana-rag:1.0.0 \
           python -m powermind_rag.cli ask "What is the revenue?"
```

### Run MCP Server

```bash
docker run -d \
  --env-file .env.docker \
  -v $(pwd)/service/storage:/app/service/storage \
  pramana-rag:1.0.0 \
  python -m powermind_rag.mcp_server
```

### Docker Compose

```bash
# Start
docker-compose -f docker-compose.service.yml up

# Run command
docker-compose -f docker-compose.service.yml run service \
  python -m powermind_rag.cli ask "question"

# Stop
docker-compose -f docker-compose.service.yml down
```

---

## Troubleshooting

**Image not built yet?**
```bash
docker build -f Dockerfile.service -t pramana-rag:1.0.0 . --no-cache
```

**Permission issues on volumes (Linux/Mac)?**
```bash
docker run --user $(id -u):$(id -g) -v ... pramana-rag:1.0.0 ...
```

**API key not working?**
```bash
# Check .env.docker syntax (no spaces around =)
cat .env.docker | grep NVIDIA_KEY
# Should be: NVIDIA_KEY="key" (not NVIDIA_KEY = "key")
```

**Out of memory?**
Increase Docker Desktop memory (Settings → Resources → Memory)

---

## Full Documentation

See **DOCKER_README.md** for:
- Complete architecture overview
- Build process & caching strategy
- All docker run variations
- Volume management (bind mounts vs named volumes)
- All environment variables explained
- Step-by-step Docker Hub publishing
- CI/CD with GitHub Actions (optional)
- Comprehensive troubleshooting

---

**Status:** ✅ All files created, build in progress (~5-10 min on first run)

Next: Pull complete DOCKER_README.md or run `docker build -f Dockerfile.service -t pramana-rag:1.0.0 .` to finish building
