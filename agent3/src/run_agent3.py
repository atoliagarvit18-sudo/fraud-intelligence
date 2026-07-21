from transcriber import transcribe_audio
from analyzer import analyze_transcript
from semantic_analyzer import semantic_analysis
from llm_analyzer import analyze_with_llm
from voice_analyzer import analyze_voice
from decision_engine import make_final_decision

import time
from pathlib import Path
from datetime import datetime


def run_agent3(audio_path=None, transcript=None):

    start_time = time.time()

    language = None
    voice_result = None

    print("========================================")
    print("Agent 3 - Scam Call Intelligence")
    print("========================================")


    # ----------------------------------------
    # Step 1 - Speech to Text (optional)
    # ----------------------------------------

    if transcript:
        print("Using provided transcript")

    elif audio_path:
        print("Transcribing audio...")

        transcription = transcribe_audio(audio_path)

        transcript = transcription["text"]
        language = transcription["language"]

    else:
        raise ValueError(
            "Either audio_path or transcript required"
        )


    print("\nTranscript:")
    print(transcript)


    # ----------------------------------------
    # Text Analysis
    # ----------------------------------------

    print("\nRunning Keyword Analyzer...")
    keyword_result = analyze_transcript(transcript)


    print("Running Semantic Analyzer...")
    semantic_result = semantic_analysis(transcript)


    print("Running LLM Analyzer...")
    llm_result = analyze_with_llm(transcript)


    # ----------------------------------------
    # Voice Analysis (only if audio exists)
    # ----------------------------------------

    if audio_path:
        print("Running Voice Analysis...")
        voice_result = analyze_voice(audio_path)


    # ----------------------------------------
    # Final Decision
    # ----------------------------------------

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

            "llm_model": "Groq Llama-3.1-8B-Instant",

            "voice_library": "Librosa"

        }
    }


    return output