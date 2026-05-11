# Pramana FastMCP Server

Pramana can run as a local or remote MCP server with FastMCP. The preferred
tool is `retrieve_evidence`: it returns cited evidence chunks and an answering
contract, while the LLM in the calling MCP host performs the final inference.

Deployed MCP endpoint:

```text
https://pramana.fastmcp.app/mcp
```

## Install With uv

```powershell
cd D:\PowerMind
uv sync --project service
```

## Local Server

Use stdio when the MCP client runs the server process locally.

```powershell
cd D:\PowerMind
uv run --project service fastmcp run service\src\powermind_rag\mcp_server.py --transport stdio
```

Direct module form:

```powershell
cd D:\PowerMind
uv run --project service python -m powermind_rag.mcp_server --transport stdio
```

## Remote Server

Use HTTP when the MCP client connects over the network.

```powershell
cd D:\PowerMind
uv run --project service fastmcp run service\src\powermind_rag\mcp_server.py --transport http --host 0.0.0.0 --port 8000
```

MCP clients connect to:

```text
http://localhost:8000/mcp/
```

The deployed server is available at:

```text
https://pramana.fastmcp.app/mcp
```

Direct module form:

```powershell
cd D:\PowerMind
uv run --project service python -m powermind_rag.mcp_server --transport http --host 0.0.0.0 --port 8000
```

For hosted deployment builders that inspect an entrypoint file, use:

```text
service/src/powermind_rag/mcp_server.py
```

The file bootstraps `service/src` onto `sys.path`, so inspection can import
`powermind_rag` even when the package has not been installed first.

## Credentials

The server does not require credentials during build or FastMCP inspection.
Credentials can be supplied at runtime through MCP tools:

1. Call `environment_status`.
2. If it reports missing variables, ask the user only for those values.
3. Call `configure_environment` with an `env` object.
4. Call `retrieve_evidence` or `ingest_pdf`.

Example `configure_environment` payload:

```json
{
  "env": {
    "NVIDIA_KEY": "your-nvidia-key",
    "GEMINI_API_KEY_1": "your-gemini-key"
  }
}
```

Common variables:

- `NVIDIA_KEY`: required for NVIDIA embeddings during retrieval and ingestion.
- `GEMINI_API_KEY_1`: required when Gemini relevance grading or Gemini visual understanding is enabled.
- `MISTRAL_API_KEY`: optional; used for Mistral OCR during ingestion if present.
- `POWERMIND_STORAGE_DIR`: optional; defaults from the app config.
- `POWERMIND_RELEVANCE_PROVIDER`: set to `lexical` or call `retrieve_evidence` with `use_relevance=false` if you want retrieval without Gemini relevance grading.

`configure_environment` stores values only in the running server process. For
permanent deployment credentials, configure them in the deployment platform's
secret manager or environment settings.

## Available Tools

- `environment_status()`: reports configured and missing environment variables without returning secret values.
- `configure_environment(env)`: sets allowed Pramana environment variables in the running server process.
- `retrieve_evidence(query, top_k, use_relevance)`: returns cited text/image evidence for host-side answering. `use_relevance` defaults to `false`, so normal retrieval only needs the NVIDIA embedding key.
- `ingest_pdf(pdf_path, doc_type, section, context)`: ingests a PDF into Pramana storage.
- `list_documents()`: lists stored documents.

## Host-Side Answering

The MCP host's LLM should answer from `retrieve_evidence` output only:

- Use only the returned `evidence` array.
- Cite every factual claim with the provided `citation`.
- If the evidence does not support the answer, say: `Not found in the document.`
