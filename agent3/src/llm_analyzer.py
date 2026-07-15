import json
import os
from pathlib import Path

from semantic_analyzer import semantic_analysis
from dotenv import load_dotenv
from groq import Groq

env_path = (Path(__file__).resolve().parent.parent / ".env")

load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise Exception("GROQ_API_KEY not found.")

client = Groq(api_key=api_key)

ALLOWED_SCAMS = [
    "Digital Arrest",
    "Bank Fraud",
    "KYC Scam",
    "Lottery Scam",
    "Investment Scam",
    "Courier Scam",
    "Job Scam",
    "Unknown"
]

def analyze_with_llm(transcript):

    semantic = semantic_analysis(transcript)
    top_examples = semantic["top_matches"]
    evidence = ""

    for i, example in enumerate(top_examples, start=1):
        evidence += (
            f"{i}. "
            f"[{example['type']}] "
            f"{example['text']} "
            f"(Similarity={example['similarity']})\n"
        )

    prompt = f"""

    You are an expert cybercrime investigator
    specializing in Indian telecom fraud.

    Analyze the phone call transcript and determine
    whether it is a scam.

    The transcript may contain:
    - English
    - Hindi
    - Hinglish
    - Grammar mistakes
    - Whisper transcription errors

    Do not rely only on keywords.
    Understand:
    - intent
    - threats
    - urgency
    - authority impersonation
    - requests for money
    - requests for personal information

    Allowed scam types:
    - Digital Arrest
    - Bank Fraud
    - KYC Scam
    - Lottery Scam
    - Investment Scam
    - Courier Scam
    - Job Scam
    - Unknown

    Retrieved evidence from knowledge base:
    {evidence}

    Use this only as supporting evidence.
    Do not copy examples directly.

    Transcript:
    ---------------------
    {transcript}
    ---------------------

    Return ONLY JSON.
    Format:
    {{
        "scam_type":"",
        "risk_score":0,
        "confidence":0.0,
        "psychological_tactics":[],
        "government_entities":[],
        "financial_request":false,
        "reasoning":[],
        "summary":""
    }}
    Rules:
    1. scam_type MUST exactly match one of the allowed categories.
    2. If this is a normal conversation,
    use "Unknown".
    3. confidence must be between 0 and 1.
    4. risk_score must be between 0 and 100.
    5. reasoning must contain exactly 3 short points.
    6. Output ONLY JSON.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    text = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]

        if lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return {
            "scam_type": "Unknown",
            "risk_score": 0,
            "confidence": 0,
            "psychological_tactics": [],
            "government_entities": [],
            "financial_request": False,
            "reasoning": [
                "LLM returned invalid JSON.",
                "Unable to analyze transcript.",
                "Fallback classification applied."
            ],
            "summary":
                "Analysis failed."
        }

    if (result.get("scam_type") not in ALLOWED_SCAMS):
        result["scam_type"] = "Unknown"

    if not result.get("scam_type"):
        result["scam_type"] = "Unknown"

    if not isinstance(result.get("risk_score"), (int,float)):
        result["risk_score"] = 0

    result["risk_score"] = max(0, min(100, result["risk_score"]))

    if not isinstance(result.get("confidence"), (int,float)):
        result["confidence"] = 0

    result["confidence"] = max( 0, min(1, result["confidence"]))
    return result

if __name__ == "__main__":
    transcript = """
    Hello sir.
    Your Aadhaar card has been linked
    to illegal activities.
    Stay on the call.
    Press one to talk to Cyber Crime.
    """
    result = analyze_with_llm(transcript)
    print(json.dumps( result, indent=4))