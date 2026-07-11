import whisper
import json
from datetime import datetime
from pathlib import Path
from analyzer import analyze_transcript

print("Loading Whisper model...")
model = whisper.load_model("base")

audio_path = "audio/sample.mp3"

print("Transcribing audio...")
result = model.transcribe(audio_path)
analysis = analyze_transcript(result["text"])

output = {
    "agent": "Agent3",
    "audio_file": Path(audio_path).name,
    "timestamp": datetime.now().isoformat(),
    "language": result["language"],
    "transcript": result["text"].strip(),
    "analysis": analysis
}

Path("output").mkdir(exist_ok=True)

with open("output/transcript.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print("\nTranscript:")
print(result["text"])

print("\nSaved to output/transcript.json")