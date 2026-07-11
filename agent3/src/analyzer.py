import re

def analyze_transcript(transcript):
    transcript = transcript.lower()

    keywords = {
        "Digital Arrest": [
            "aadhaar",
            "aadhar",
            "cbi",
            "ed",
            "cyber crime",
            "customs",
            "illegal activities",
            "money laundering",
            "press one",
            "transfer",
            "bank account"
        ]
    }

    detected_keywords = []
    scam_type = "Unknown"
    risk = "Low"

    for scam, words in keywords.items():
        for word in words:

            if " " in word:
                # Multi-word phrase
                if word in transcript:
                    detected_keywords.append(word)
            else:
                # Match whole words only
                if re.search(r"\b" + re.escape(word) + r"\b", transcript):
                    detected_keywords.append(word)

        if detected_keywords:
            scam_type = scam

    detected_keywords = list(set(detected_keywords))

    if len(detected_keywords) >= 4:
        risk = "High"
    elif len(detected_keywords) >= 2:
        risk = "Medium"

    return {
        "scam_type": scam_type,
        "risk": risk,
        "keywords": detected_keywords
    }