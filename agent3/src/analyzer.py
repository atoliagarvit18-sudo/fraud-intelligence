import re

def normalize_transcript(text):
    text = text.lower()
    text = text.replace("cybercrime", "cyber crime")
    return text

def analyze_transcript(transcript):

    transcript = normalize_transcript(transcript)
    scam_patterns = {

        "Digital Arrest": {

            "cbi": 25,
            "ed": 25,
            "customs": 20,
            "cyber crime": 20,
            "money laundering": 20,
            "illegal activities": 15,
            "aadhaar": 10,
            "press one": 10,
            "transfer": 8,
            "bank account": 8,
        },

        "Bank Fraud": {

            "otp": 25,
            "cvv": 25,
            "upi": 20,
            "upi pin": 25,
            "bank manager": 20,
            "debit card": 15,
            "credit card": 15,
            "verify account": 15,
            "account blocked": 15,
            "net banking": 10,
        },

        "KYC Scam": {

            "kyc": 25,
            "pan": 15,
            "verification": 15,
            "update account": 15,
            "download app": 20,
            "install app": 20,
            "apk": 25,
            "click link": 15,
        }
    }

    best_score = 0
    scam_type = "Unknown"
    detected_keywords = []

    for scam, words in scam_patterns.items():

        current_score = 0
        current_keywords = []

        for word, weight in words.items():

            if " " in word:

                if word in transcript:
                    current_keywords.append(word)
                    current_score += weight

            else:

                if re.search(r"\b" + re.escape(word) + r"\b", transcript):
                    current_keywords.append(word)
                    current_score += weight

        if current_score > best_score:
            best_score = current_score
            scam_type = scam
            detected_keywords = current_keywords

    score = min(best_score, 100)

    if score >= 70:
        risk_level = "High"
        severity_color = "red"

    elif score >= 40:
        risk_level = "Medium"
        severity_color = "orange"

    else:
        risk_level = "Low"
        severity_color = "green"

    confidence = round(score / 100, 2)

    if detected_keywords:
        explanation = (
            f"Detected {len(detected_keywords)} keyword indicators: "
            + ", ".join(detected_keywords)
            + "."
        )
    else:
        explanation = (
            "No strong keyword indicators detected. "
            "Semantic analysis will determine the final classification."
        )

    return {
        "scam_type": scam_type,
        "risk_score": score,
        "risk_level": risk_level,
        "confidence": confidence,
        "scam_probability": f"{score}%",
        "severity_color": severity_color,
        "keywords": detected_keywords,
        "explanation": explanation
    }