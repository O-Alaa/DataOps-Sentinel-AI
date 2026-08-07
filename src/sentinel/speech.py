from __future__ import annotations

import os
import tempfile
import time
from functools import lru_cache

from sentinel.config import settings


@lru_cache(maxsize=1)
def get_whisper_model():
    from faster_whisper import WhisperModel

    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def _local_transcription(audio_bytes: bytes, suffix: str) -> dict:
    started = time.perf_counter()
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(audio_bytes)
            temp_path = f.name

        model = get_whisper_model()
        segments, info = model.transcribe(
            temp_path,
            beam_size=settings.whisper_beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        segments = list(segments)
        text = " ".join(segment.text.strip() for segment in segments).strip()

        return {
            "text": text,
            "language": info.language,
            "language_probability": round(float(info.language_probability), 4),
            "audio_duration_seconds": round(float(info.duration), 2),
            "transcription_latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "segments": [
                {
                    "start": round(float(segment.start), 2),
                    "end": round(float(segment.end), 2),
                    "text": segment.text.strip(),
                }
                for segment in segments
            ],
            "transcription_provider": "faster-whisper-local",
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def _segment_value(segment, key: str, default=None):
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


def _groq_transcription(audio_bytes: bytes, suffix: str) -> dict:
    if not settings.groq_api_key.strip():
        raise RuntimeError("GROQ_API_KEY is required when STT_PROVIDER=groq.")

    from groq import Groq

    started = time.perf_counter()
    client = Groq(api_key=settings.groq_api_key)
    filename = f"incident{suffix or '.wav'}"

    response = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=settings.groq_whisper_model,
        response_format="verbose_json",
        timestamp_granularities=["segment"],
        temperature=0.0,
    )

    raw_segments = getattr(response, "segments", None) or []
    segments = [
        {
            "start": round(float(_segment_value(segment, "start", 0.0)), 2),
            "end": round(float(_segment_value(segment, "end", 0.0)), 2),
            "text": str(_segment_value(segment, "text", "")).strip(),
        }
        for segment in raw_segments
    ]

    duration = getattr(response, "duration", 0.0) or 0.0
    language = getattr(response, "language", "") or "unknown"

    return {
        "text": str(getattr(response, "text", "")).strip(),
        "language": language,
        "language_probability": 0.0,
        "audio_duration_seconds": round(float(duration), 2),
        "transcription_latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "segments": segments,
        "transcription_provider": f"groq:{settings.groq_whisper_model}",
    }


def transcribe_audio_bytes(audio_bytes: bytes, suffix: str = ".wav") -> dict:
    """Transcribe audio using the configured local or managed provider."""
    provider = settings.stt_provider.strip().lower()

    if provider == "local":
        return _local_transcription(audio_bytes, suffix)
    if provider == "groq":
        return _groq_transcription(audio_bytes, suffix)

    raise ValueError(
        f"Unsupported STT_PROVIDER={settings.stt_provider!r}. "
        "Supported providers: local, groq."
    )
