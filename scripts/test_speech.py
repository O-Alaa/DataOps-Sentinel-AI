import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sentinel.speech import transcribe_audio_bytes

if len(sys.argv) < 2:
    raise SystemExit(
        "Usage: python scripts/test_speech.py path\\to\\audio.wav"
    )

audio_path = Path(sys.argv[1])
result = transcribe_audio_bytes(
    audio_path.read_bytes(),
    suffix=audio_path.suffix,
)

print("=== TRANSCRIPTION ===")
print(result["text"])
print("\nLanguage:", result["language"])
print("Language probability:", result["language_probability"])
print("Audio duration:", result["audio_duration_seconds"])
print("Latency ms:", result["transcription_latency_ms"])
