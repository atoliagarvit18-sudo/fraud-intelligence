from transcriber import transcribe_audio
from analyzer import analyze_transcript
from semantic_analyzer import semantic_analysis
from llm_analyzer import analyze_with_llm
from voice_analyzer import analyze_voice
from decision_engine import make_final_decision

import json
import time
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

AUDIO_PATH = "audio/sample.mp3"

start_time = time.time()

print("========================================")
print("Agent 3 - Scam Call Intelligence")
print("========================================\n")


# ---------------------------------------------------
# Step 1 - Speech to Text
# ---------------------------------------------------

print("Loading Whisper...")
print("Transcribing audio...\n")

transcription = transcribe_audio(AUDIO_PATH)

transcript = transcription["text"]
language = transcription["language"]

print("Transcript:\n")
print(transcript)
print()

print("Running Keyword Analyzer...")

keyword_result = analyze_transcript(transcript)

print("Running Semantic Analyzer...")

semantic_result = semantic_analysis(transcript)

print("Running LLM Analyzer...")

llm_result = analyze_with_llm(transcript)

print("Running Voice Analysis...")

voice_result = analyze_voice(AUDIO_PATH)

print("Building Final Decision...\n")

overall_analysis = make_final_decision(
    keyword_result,
    semantic_result,
    llm_result
)

processing_time = round(
    time.time() - start_time,
    2
)

output = {

    "agent": "Agent3",

    "audio_file": Path(AUDIO_PATH).name,

    "timestamp": datetime.now().isoformat(),

    "language": language,

    "transcript": transcript,

    "keyword_analysis": keyword_result,

    "semantic_analysis": semantic_result,

    "llm_analysis": llm_result,

    "voice_analysis": voice_result,

    "overall_analysis": overall_analysis,

    "system": {

        "processing_time_seconds": processing_time,

        "speech_model": "Whisper Base",

        "semantic_model": "SentenceTransformer all-MiniLM-L6-v2",

        "llm_model": "Groq Llama-3.1-8B-Instant (RAG)",

        "voice_library": "Librosa"

    }

}

Path("output").mkdir(exist_ok=True)

with open(
    "output/transcript.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\n========================================")
print("FINAL ANALYSIS")
print("========================================\n")

print(json.dumps(output, indent=4, ensure_ascii=False))

print("\nSaved to output/transcript.json")