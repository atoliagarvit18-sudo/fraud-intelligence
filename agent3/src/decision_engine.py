def make_final_decision(keyword_result, semantic_result, voice_result):

    keyword_score = keyword_result["risk_score"]

    semantic_score = int(semantic_result["semantic_similarity"] * 100)

    voice_score = 10 if voice_result["audio_quality"] == "Good" else 5

    final_score = (
        keyword_score * 0.4 +
        semantic_score * 0.5 +
        voice_score * 0.1
    )

    final_score = round(final_score)

    if final_score >= 70:
        risk = "High"
        color = "red"

    elif final_score >= 40:
        risk = "Medium"
        color = "orange"

    else:
        risk = "Low"
        color = "green"

    return {
        "predicted_scam": semantic_result["predicted_scam"],
        "final_risk_score": final_score,
        "risk_level": risk,
        "severity_color": color,
        "confidence": round(final_score / 100, 2),
        "keyword_score": keyword_score,
        "semantic_score": semantic_score,
        "voice_score": voice_score
    }