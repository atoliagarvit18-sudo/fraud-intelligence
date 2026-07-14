from transcriber import transcribe_audio
import time
import json
from datetime import datetime
from pathlib import Path

from analyzer import analyze_transcript
from semantic_analyzer import semantic_analysis
from voice_analyzer import analyze_voice

start_time = time.time()
audio_path = "audio/sample.mp3"

result = transcribe_audio(audio_path)

transcript = result["text"]

language = result["language"]
keyword_analysis = analyze_transcript(transcript)
semantic = semantic_analysis(transcript)

voice = analyze_voice(audio_path)

keyword_score = keyword_analysis["risk_score"]

semantic_score = int(
    semantic["semantic_similarity"] * 100
)

model_agreement = (
    keyword_analysis["scam_type"] ==
    semantic["predicted_scam"]
)

final_score = int(
    0.40 * keyword_score +
    0.60 * semantic_score
)

if final_score >= 70:
    risk_level = "High"
    severity_color = "red"

elif final_score >= 40:
    risk_level = "Medium"
    severity_color = "orange"

else:
    risk_level = "Low"
    severity_color = "green"

if risk_level == "High":
    recommendation = (
        "Disconnect the call immediately and report it."
    )

elif risk_level == "Medium":
    recommendation = (
        "Proceed cautiously and verify independently."
    )

else:
    recommendation = (
        "No major scam indicators detected."
    )

analysis = {
    "keyword_prediction": keyword_analysis["scam_type"],
    "semantic_prediction": semantic["predicted_scam"],
    "final_prediction": semantic["predicted_scam"],
    "keyword_score": keyword_score,
    "semantic_similarity": round(semantic["semantic_similarity"],3),
    "semantic_scores": semantic["all_scores"],
    "final_risk_score": final_score,
    "risk_level": risk_level,
    "confidence": round(final_score/100,2),
    "scam_probability": f"{final_score}%",
    "severity_color": severity_color,
    "model_agreement": model_agreement,
    "keywords": keyword_analysis["keywords"],
    "recommendation": recommendation,
    "explanation": keyword_analysis["explanation"]
}

output = {
    "agent": "Agent3",
    "audio_file": Path(audio_path).name,
    "timestamp": datetime.now().isoformat(),
    "language": language,
    "transcript": transcript,
    "keyword_analysis": keyword_analysis,
    "semantic_analysis": semantic,
    "voice_analysis": voice,
    "overall_analysis": analysis
}

processing_time = round(
    time.time() - start_time,
    2
)

output["system"] = {
    "processing_time_seconds": processing_time,
    "speech_model": "Whisper Base",
    "semantic_model": "SentenceTransformer all-MiniLM-L6-v2",
    "voice_library": "Librosa"
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

print("\nTranscript:")
print(transcript)

print("\nFinal Output:")
print(json.dumps(output, indent=4))

print("\nSaved to output/transcript.json")