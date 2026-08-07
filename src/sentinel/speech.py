from __future__ import annotations

import os
import tempfile
import time
from functools import lru_cache

from faster_whisper import WhisperModel

from sentinel.config import settings


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_audio_bytes(audio_bytes: bytes, suffix: str = ".wav") -> dict:
    """
    The temporary audio file is deleted immediately after transcription.
    """
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
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
