# Environment Format

This is the cleaned environment format for Pramana based on the variables used
by the current project. Do not commit real credentials. Use this as a deployment
secret checklist or as a local `.env` template.

## Minimal MCP Retrieval

For the MCP `retrieve_evidence` tool with `use_relevance=false`, the minimum is:

```env
NVIDIA_KEY="<your-nvidia-api-key>"
NVIDIA_EMBEDDING_MODEL="nvidia/nv-embed-v1"
NVIDIA_VLM_BASE_URL="https://integrate.api.nvidia.com/v1"
POWERMIND_STORAGE_DIR="/app/service/storage"
POWERMIND_DEVICE="api"
POWERMIND_RELEVANCE_PROVIDER="lexical"
POWERMIND_ENABLE_COLPALI_VISUAL_INDEX="0"
POWERMIND_ENABLE_QUERY_VISUAL_RETRIEVAL="0"
```

For local Windows development, `POWERMIND_STORAGE_DIR` can be:

```env
POWERMIND_STORAGE_DIR="D:\PowerMind\service\storage"
```

## Recommended API-First Deployment

```env
# Storage/runtime
POWERMIND_STORAGE_DIR="/app/service/storage"
POWERMIND_DEVICE="api"
POWERMIND_LOCAL_ONLY="0"
PYTHONDONTWRITEBYTECODE="1"

# NVIDIA embeddings and VLM fallback
NVIDIA_KEY="<your-nvidia-api-key>"
NVIDIA_EMBEDDING_MODEL="nvidia/nv-embed-v1"
NVIDIA_VLM_MODEL="microsoft/phi-4-multimodal-instruct"
NVIDIA_GENERATION_MODEL="microsoft/phi-4-multimodal-instruct"
NVIDIA_VLM_BASE_URL="https://integrate.api.nvidia.com/v1"

# Gemini relevance / visual understanding
GEMINI_API_KEY_1="<your-gemini-api-key-1>"
GEMINI_API_KEY_2="<optional-gemini-api-key-2>"
GEMINI_API_KEY_3="<optional-gemini-api-key-3>"
GEMINI_API_KEY_4="<optional-gemini-api-key-4>"
GEMINI_API_KEY_5="<optional-gemini-api-key-5>"
GEMINI_API_KEY_6="<optional-gemini-api-key-6>"
GEMINI_RELEVANCE_MODEL="gemini-2.5-flash"

# Mistral OCR
MISTRAL_API_KEY="<your-mistral-api-key>"
MISTRAL_SERVER_URL="https://api.mistral.ai"
MISTRAL_TIMEOUT_MS="120000"

# Retrieval/relevance
POWERMIND_RELEVANCE_PROVIDER="gemini"
POWERMIND_ALLOW_LEXICAL_CRAG_FALLBACK="0"
POWERMIND_ENABLE_QUERY_VISUAL_RETRIEVAL="0"
POWERMIND_ENABLE_COLPALI_VISUAL_INDEX="0"
POWERMIND_LOAD_IMPORTED_RECORDS="0"

# Ingestion visual understanding
POWERMIND_ENABLE_VISUAL_UNDERSTANDING="true"
POWERMIND_VISUAL_UNDERSTANDING_PROVIDER="gemini_nvidia"
POWERMIND_REFRESH_VISUAL_UNDERSTANDING="0"

# Generation used by CLI/full pipeline, not required for MCP evidence-only answering
POWERMIND_GENERATION_PROVIDER="nvidia"
POWERMIND_IMAGE_PROVIDER="nvidia_gemini"
POWERMIND_ENABLE_QUERY_VLM_FALLBACK="1"
POWERMIND_INCLUDE_PAGE_IMAGES_IN_ANSWERS="0"

# Chunking
POWERMIND_CHUNKING_PROVIDER="rules"
POWERMIND_CHUNKING_FALLBACK_PROVIDER="none"
GEMINI_CHUNKING_MODEL="gemini-2.5-flash"
GROQ_CHUNKING_MODEL="llama-3.3-70b-versatile"

# Optional verification
POWERMIND_ENABLE_VERIFICATION="0"
LETTUCE_MODEL_PATH="KRLabsOrg/lettucedect-base-modernbert-en-v1"
```

## Optional Providers

Only set these if you intentionally use Groq or OpenRouter paths:

```env
GROQ_API_KEY="<your-groq-api-key>"
GROQ_RELEVANCE_MODEL="llama-3.1-8b-instant"
GROQ_GENERATION_MODEL="llama-3.3-70b-versatile"

OPEN_ROUTER_API_KEY="<your-openrouter-api-key>"
OPEN_ROUTER_GENERATION_MODEL="liquid/lfm-2.5-1.2b-instruct:free"
```

## Optional Local Model Paths

The default deployment does not need local models. Keep these unset unless you
are deliberately running local experiments:

```env
QWEN_MODEL_PATH="D:\PowerMind\Qwen"
QWEN_VL_MODEL_PATH="D:\PowerMind\Qwen_VL"
QWEN_VL_DEVICE="cuda"
QWEN_VL_VISUAL_MAX_TOKENS="384"
POWERMIND_CUDA_ARCH="sm_120"
```

## Runtime MCP Credential Flow

If you cannot provide all credentials upfront, the MCP host can configure only
what is missing:

1. Call `environment_status`.
2. Ask the user for the variables listed in `missing_for_retrieval` or `missing_for_ingest`.
3. Call `configure_environment`:

```json
{
  "env": {
    "NVIDIA_KEY": "<your-nvidia-api-key>",
    "GEMINI_API_KEY_1": "<your-gemini-api-key>"
  }
}
```

These values are set only for the running MCP server process. For permanent
hosted deployment, put the same variables in the platform secret manager.

## Notes

- `NVIDIA_KEY` is the main required key for retrieval because NVIDIA embeddings are used.
- Gemini keys are only needed for Gemini relevance grading, Gemini chunking, or Gemini visual understanding.
- `MISTRAL_API_KEY` is only needed for OCR during ingestion.
- Avoid duplicate keys in `.env`; the last duplicate value usually wins, which makes debugging painful.

