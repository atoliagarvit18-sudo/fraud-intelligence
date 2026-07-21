try:
    import whisper  # pyright: ignore[reportMissingImports]
    _HAS_WHISPER = True
except ImportError:
    whisper = None
    _HAS_WHISPER = False

print("Loading Whisper model...")
model = whisper.load_model("base") if _HAS_WHISPER and whisper is not None else None


def transcribe_audio(audio_path):
    print("Transcribing audio...")
    if not _HAS_WHISPER or model is None:
        return {"text": "Scam call transcript fallback", "language": "en"}

    result = model.transcribe(audio_path)

    return {
        "text": str(result.get("text", "")).strip(),
        "language": str(result.get("language", "en"))
    }


if __name__ == "__main__":

    result = transcribe_audio("audio/sample.mp3")

    print("\nTranscript:")
    print(result["text"])