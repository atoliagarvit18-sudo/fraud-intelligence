import re

def normalize_transcript(text):
    text = text.lower()

    replacements = {
        "cybercrime": "cyber crime",
        "cyber-crime": "cyber crime",
        "aadhaar card": "aadhaar",
        "aadhar card": "aadhaar",
        "upi pin": "upi pin"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def analyze_transcript(transcript):

    transcript = normalize_transcript(transcript)
    scam_patterns = {

        "Digital Arrest": {
            "cbi": 25,
            "enforcement directorate": 25,
            "ed officer": 25,
            "cyber crime department": 25,
            "cyber crime cell": 25,
            "arrest warrant": 25,
            "video verification": 20,
            "stay on the call": 15,
            "money laundering": 20,
            "aadhaar": 15,
            "parcel case": 15,
            "customs": 15,
            "press one": 10,
            "illegal activities": 10
        },

        "Bank Fraud": {
            "otp": 30,
            "cvv": 30,
            "upi pin": 30,
            "upi": 20,
            "bank account": 15,
            "account blocked": 20,
            "debit card": 20,
            "credit card": 20,
            "net banking": 20,
            "verify account": 15,
            "bank manager": 15
        },

        "KYC Scam": {
            "kyc": 30,
            "pan card": 20,
            "pan": 15,
            "verification": 15,
            "update kyc": 25,
            "download app": 25,
            "install app": 25,
            "apk": 30,
            "click link": 20,
            "sim blocked": 20
        },

        "Courier Scam": {
            "parcel": 25,
            "customs": 20,
            "courier": 25,
            "package": 20,
            "shipment": 20,
            "delivery": 15,
            "illegal item": 25,
            "release parcel": 20
        },

        "Investment Scam": {
            "investment": 30,
            "guaranteed return": 30,
            "double money": 25,
            "profit": 15,
            "crypto": 25,
            "trading": 20,
            "stock market": 20,
            "earn money": 20
        },

        "Lottery Scam": {
            "lottery": 30,
            "prize": 25,
            "winner": 20,
            "reward": 20,
            "claim amount": 20,
            "processing fee": 25
        },

        "Job Scam": {
            "job": 20,
            "work from home": 25,
            "selection": 20,
            "registration fee": 30,
            "joining fee": 30,
            "salary": 15,
            "interview": 15
        }
    }

    scores = {}
    keyword_hits = {}

    for scam, words in scam_patterns.items():
        score = 0
        hits = []

        for word, weight in words.items():
            if word in transcript:
                score += weight
                hits.append(word)
        
        scores[scam] = score
        keyword_hits[scam] = hits

    if ("cyber crime" in transcript and "aadhaar" in transcript):
        scores["Digital Arrest"] += 25
        keyword_hits["Digital Arrest"].append("cyber crime + aadhaar combination")

    if ("otp" in transcript and "bank" in transcript):
        scores["Bank Fraud"] += 20
        keyword_hits["Bank Fraud"].append("otp + bank combination")

    if ("kyc" in transcript and "apk" in transcript):
        scores["KYC Scam"] += 20
        keyword_hits["KYC Scam"].append("kyc + apk combination")

    scam_type = max(scores, key=lambda k: scores.get(k, 0))

    best_score = scores[scam_type]
    detected_keywords = keyword_hits[scam_type]

    if best_score < 20:
        scam_type = "Unknown"
        best_score = 0
        detected_keywords = []

    score = min(best_score,100)

    if score >= 70:
        risk_level = "High"
        severity_color = "red"
    elif score >= 40:
        risk_level = "Medium"
        severity_color = "orange"
    else:
        risk_level = "Low"
        severity_color = "green"

    confidence = round(score / 100,2)

    if detected_keywords:
        explanation = (
            f"Detected {len(detected_keywords)} indicators: "
            + ", ".join(detected_keywords)
            + "."
        )
    else:
        explanation = (
            "No strong keyword indicators detected. "
            "Semantic and LLM analysis required."
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