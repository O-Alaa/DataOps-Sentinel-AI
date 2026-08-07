# Fully Hosted Deployment (Option B)

This profile runs without the developer laptop at runtime.

## Architecture

Streamlit Community Cloud
→ public Railway FastAPI
→ Railway private network
→ LangGraph
→ Data A2A Agent → MCP → DuckDB/log evidence
→ Knowledge A2A Agent → Hybrid RAG → Qdrant Cloud
→ Groq-hosted Qwen → deterministic grounding/validator

Voice transcription uses Groq-hosted Whisper in the cloud profile.

The existing local Docker/Ollama profile remains available and unchanged.

## Services

Create four services in one Railway project, all from this GitHub repository:

1. `sentinel-api`
   - Dockerfile: `deploy/railway/Dockerfile.api`
   - Public domain: YES
2. `sentinel-mcp`
   - Dockerfile: `deploy/railway/Dockerfile.mcp`
   - Public domain: NO
3. `sentinel-data-agent`
   - Dockerfile: `deploy/railway/Dockerfile.data-agent`
   - Public domain: NO
4. `sentinel-knowledge-agent`
   - Dockerfile: `deploy/railway/Dockerfile.knowledge-agent`
   - Public domain: NO

The fixed internal ports are:
- MCP: 8100
- Data Agent: 8201
- Knowledge Agent: 8202

The API listens on Railway's injected `$PORT`.

## 1. Create Qdrant Cloud

Create a free Qdrant Cloud cluster.

Copy:
- cluster URL
- API key

Use the same collection name everywhere:

`sentinel_knowledge`

The Knowledge Agent can rebuild the tiny demo index automatically on startup.

## 2. Create a Groq API key

The cloud profile uses:

- LLM: `qwen/qwen3.6-27b`
- STT: `whisper-large-v3-turbo`

Do not commit the key to GitHub.

## 3. Create the Railway project

Connect:

`O-Alaa/DataOps-Sentinel-AI`

Create the four services above from the same repository and assign each service
its Dockerfile path.

Railway private DNS names use:

`<service-name>.railway.internal`

### MCP service variables

```env
SERVICE_HOST=0.0.0.0
```

No public domain is required.

### Data Agent variables

```env
SERVICE_HOST=0.0.0.0
MCP_SERVER_URL=http://sentinel-mcp.railway.internal:8100/mcp
A2A_DATA_AGENT_URL=http://sentinel-data-agent.railway.internal:8201
```

No public domain is required.

### Knowledge Agent variables

```env
SERVICE_HOST=0.0.0.0

A2A_KNOWLEDGE_AGENT_URL=http://sentinel-knowledge-agent.railway.internal:8202

QDRANT_URL=<YOUR_QDRANT_CLUSTER_URL>
QDRANT_API_KEY=<YOUR_QDRANT_API_KEY>
QDRANT_COLLECTION=sentinel_knowledge

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_BACKEND=fastembed
RAG_TOP_K=3
RAG_AUTO_INGEST=true
RAG_RECREATE_ON_START=true
```

No public domain is required.

### API service variables

Generate one strong random API key and keep it private.

```env
SERVICE_HOST=0.0.0.0

LLM_PROVIDER=groq
GROQ_API_KEY=<YOUR_GROQ_API_KEY>
GROQ_MODEL=qwen/qwen3.6-27b

STT_PROVIDER=groq
GROQ_WHISPER_MODEL=whisper-large-v3-turbo

QDRANT_URL=<YOUR_QDRANT_CLUSTER_URL>
QDRANT_API_KEY=<YOUR_QDRANT_API_KEY>
QDRANT_COLLECTION=sentinel_knowledge

MCP_SERVER_URL=http://sentinel-mcp.railway.internal:8100/mcp
A2A_DATA_AGENT_URL=http://sentinel-data-agent.railway.internal:8201
A2A_KNOWLEDGE_AGENT_URL=http://sentinel-knowledge-agent.railway.internal:8202

API_AUTH_KEY=<YOUR_RANDOM_SHARED_KEY>

SPACY_MODEL=en_core_web_sm
PII_SCORE_THRESHOLD=0.35
VALIDATION_MAX_RETRIES=1

OTEL_SERVICE_NAME=dataops-sentinel-ai-cloud
```

Generate a public Railway domain only for `sentinel-api`.

The unauthenticated liveness endpoint is:

`GET /health`

The following endpoints require `X-API-Key` when `API_AUTH_KEY` is set:

- `/health/dependencies`
- `/investigate`
- `/privacy-preview`
- `/transcribe`

## 4. Validate the Railway backend

First:

```bash
curl https://<YOUR-API-DOMAIN>/health
```

Then with the shared API key:

```bash
curl https://<YOUR-API-DOMAIN>/health/dependencies \
  -H "X-API-Key: <YOUR_RANDOM_SHARED_KEY>"
```

All five dependency checks should be healthy.

Then test an investigation:

```bash
curl -X POST https://<YOUR-API-DOMAIN>/investigate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <YOUR_RANDOM_SHARED_KEY>" \
  -d '{"query":"Our executive Sales KPI dashboard dropped significantly today. Investigate.","input_channel":"cloud-smoke"}'
```

## 5. Deploy Streamlit Community Cloud

Create an app from:

- Repository: `O-Alaa/DataOps-Sentinel-AI`
- Branch: `main`
- Main file: `streamlit_cloud/app.py`

The dependency file beside the entry point is:

`streamlit_cloud/requirements.txt`

Add these Streamlit secrets:

```toml
API_BASE_URL = "https://<YOUR-RAILWAY-API-DOMAIN>"
API_KEY = "<YOUR_RANDOM_SHARED_KEY>"
```

Deploy.

## 6. Re-run evaluation against cloud

The old Phase 5 metrics are the validated local Docker/Ollama baseline.

Before publishing managed-cloud accuracy/latency numbers, run the regression suite
against the Railway API and save a separate cloud result. Do not present local
latency as cloud latency.

## Security boundary

Only two components are publicly reachable:

1. Streamlit Community Cloud
2. Railway FastAPI

MCP and both A2A specialist services stay on Railway's private network.
Qdrant uses its managed HTTPS API and API-key authentication.

The public FastAPI investigation/transcription routes require the shared
`X-API-Key`; the key is stored in Streamlit secrets and Railway variables, not
in GitHub.
