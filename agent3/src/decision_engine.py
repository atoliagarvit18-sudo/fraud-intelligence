from collections import Counter

def make_final_decision(keyword_result, semantic_result, llm_result):

    predictions = [
        keyword_result["scam_type"],
        semantic_result["predicted_scam"],
        llm_result["scam_type"]
    ]

    vote_counter = Counter(predictions)
    final_prediction = vote_counter.most_common(1)[0][0]
    agreement = vote_counter[final_prediction]
    keyword_score = keyword_result["risk_score"]

    semantic_score = int(
        semantic_result["semantic_similarity"] * 100
    )

    llm_score = llm_result["risk_score"]

    base_score = ( keyword_score * 0.2 + semantic_score * 0.3 + llm_score * 0.5)

    agreement_bonus = {
        3: 10,
        2: 3,
        1: 0
    }

    final_score = min(
        round(base_score + agreement_bonus[agreement]),
        100
    )

    if final_score >= 70:
        risk = "High"

    elif final_score >= 40:
        risk = "Medium"

    else:
        risk = "Low"

    confidence = (agreement / 3 * 0.5 + semantic_result["semantic_similarity"] * 0.3 + llm_result["confidence"] * 0.2)
    confidence = round(min(confidence, 1), 2)

    reasoning = []

    reasoning.append(
        f'Keyword analyzer predicted "{keyword_result["scam_type"]}".'
    )
    reasoning.append(
        f'Semantic analyzer predicted "{semantic_result["predicted_scam"]}".'
    )
    reasoning.append(
        f'LLM predicted "{llm_result["scam_type"]}".'
    )

    if agreement == 3:
        reasoning.append(
            "All three analyzers agreed."
        )

    elif agreement == 2:
        reasoning.append(
            "Majority vote (2 out of 3 analyzers)."
        )

    else:
        reasoning.append(
            "No agreement between analyzers."
        )

    return {

        "final_prediction": final_prediction,
        "agreement": f"{agreement}/3",
        "final_risk_score": final_score,
        "risk_level": risk,
        "confidence": confidence,
        "keyword_score": keyword_score,
        "semantic_score": semantic_score,
        "llm_score": llm_score,
        "reasoning": reasoning
    }