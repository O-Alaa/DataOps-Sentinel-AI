# Deployment Guide

## Recommended Demo Deployment

The validated production architecture uses multiple services plus a local Qwen3
model. For an interview demo, the simplest zero-cloud-compute deployment is:

1. Run the full Docker stack locally.
2. Reuse native Windows Ollama for Qwen3.
3. Expose only the Streamlit frontend through a Cloudflare Quick Tunnel.

This keeps MCP, A2A, Qdrant, FastAPI and Ollama off the public Internet.

## Start the application

```powershell
docker compose -f compose.host-ollama.yaml up -d --build
```

Verify:

```powershell
docker compose -f compose.host-ollama.yaml ps
```

Run the smoke test:

```powershell
python scripts/smoke_test_stack.py
```

## Start the public demo tunnel

```powershell
docker compose `
  -f compose.host-ollama.yaml `
  -f compose.demo.yaml `
  up -d tunnel
```

Read the generated URL:

```powershell
docker compose `
  -f compose.host-ollama.yaml `
  -f compose.demo.yaml `
  logs tunnel
```

Look for a line containing a URL similar to:

```text
https://random-words.trycloudflare.com
```

Open that URL from a phone or another network to verify public access.

## Important

Quick Tunnels are temporary demo/testing infrastructure. The public hostname is
random and may change when the tunnel restarts.

For a persistent production hostname, use a named Cloudflare Tunnel or deploy
the container stack to infrastructure with sufficient memory/compute for the
LLM runtime.

## Stop the demo

Stop only the public tunnel:

```powershell
docker compose `
  -f compose.host-ollama.yaml `
  -f compose.demo.yaml `
  stop tunnel
```

Stop the whole application:

```powershell
docker compose -f compose.host-ollama.yaml down
```

## Security model

Only Streamlit is exposed through the tunnel.

The following stay on the local Docker/host network:

- FastAPI
- MCP server
- Data A2A agent
- Knowledge A2A agent
- Qdrant
- Ollama

This is intentional: the demo does not directly publish operational tool or
agent endpoints to the Internet.
