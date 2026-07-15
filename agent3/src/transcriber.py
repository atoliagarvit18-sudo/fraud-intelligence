import whisper

print("Loading Whisper model...")
model = whisper.load_model("base")


def transcribe_audio(audio_path):
    print("Transcribing audio...")

    result = model.transcribe(audio_path)

    return {
        "text": result["text"].strip(),
        "language": result["language"]
    }


if __name__ == "__main__":

    result = transcribe_audio("audio/sample.mp3")

    print("\nTranscript:")
    print(result["text"])