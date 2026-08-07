import hmac
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from sentinel.config import settings
from sentinel.graph import investigate
from sentinel.health import dependency_health
from sentinel.security import prepare_input
from sentinel.speech import transcribe_audio_bytes

app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    description=(
        "Distributed DataOps incident investigation using LangGraph, MCP, A2A, "
        "hybrid RAG, pluggable LLM/STT providers, privacy controls and "
        "deterministic validation."
    ),
)


class InvestigationRequest(BaseModel):
    query: str
    input_channel: str = "text"


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optional shared-key boundary for the public cloud API."""
    expected = settings.api_auth_key.strip()
    if not expected:
        return

    supplied = (x_api_key or "").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid API key.")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.6.0",
    }


@app.get("/health/dependencies", dependencies=[Depends(require_api_key)])
async def health_dependencies():
    return await dependency_health()


@app.post("/investigate", dependencies=[Depends(require_api_key)])
async def investigate_incident(payload: InvestigationRequest):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    return await investigate(
        payload.query,
        input_channel=payload.input_channel,
    )


@app.post("/privacy-preview", dependencies=[Depends(require_api_key)])
def privacy_preview(payload: InvestigationRequest):
    prepared = prepare_input(payload.query)
    return {
        "safe_text": prepared.safe_text,
        "pii_detected_count": prepared.pii_detected_count,
        "pii_entities": prepared.pii_entities,
        "security_flags": prepared.security_flags,
    }


@app.post("/transcribe", dependencies=[Depends(require_api_key)])
async def transcribe_audio(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    filename = file.filename or "incident.wav"

    if not (
        content_type.startswith("audio/")
        or filename.lower().endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm"))
    ):
        raise HTTPException(status_code=415, detail="Upload an audio file.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    transcription = transcribe_audio_bytes(
        audio_bytes,
        suffix=Path(filename).suffix or ".wav",
    )
    prepared = prepare_input(transcription["text"])

    return {
        **transcription,
        "safe_preview": prepared.safe_text,
        "pii_detected_count": prepared.pii_detected_count,
        "pii_entities": prepared.pii_entities,
        "security_flags": prepared.security_flags,
    }
