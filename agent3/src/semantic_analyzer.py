import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

print("Loading Semantic Model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

knowledge_path = (
    Path(__file__).parent
    / "knowledge"
    / "knowledge_base.json"
)

with open(
    knowledge_path,
    "r",
    encoding="utf-8"
) as f:
    scam_data = json.load(f)

SCAM_EXAMPLES = {}

for item in scam_data:
    scam_type = item["type"]
    text = item["text"]

    if scam_type not in SCAM_EXAMPLES:
        SCAM_EXAMPLES[scam_type] = []

    SCAM_EXAMPLES[scam_type].append(text)

pattern_embeddings = {}

for scam, examples in SCAM_EXAMPLES.items():
    pattern_embeddings[scam] = model.encode(
        examples,
        convert_to_tensor=True
    )

def semantic_analysis(transcript):
    transcript_embedding = model.encode(
        transcript,
        convert_to_tensor=True
    )

    similarities = {}
    top_matches = []

    for scam, embeddings in pattern_embeddings.items():
        scores = util.cos_sim(
            transcript_embedding,
            embeddings
        )[0]

        score_list = [
            float(s)
            for s in scores
        ]
        score_list.sort(reverse=True)

        strong_scores = [
            s for s in score_list
            if s >= 0.60
        ]

        if strong_scores:
            similarities[scam] = round(sum(strong_scores) / len(strong_scores), 3)
        else:
            similarities[scam] = round(score_list[0], 3)

        examples = SCAM_EXAMPLES[scam]

        for example, score in zip(examples, scores):
            top_matches.append({
                "type": scam,
                "text": example,
                "similarity": round(float(score), 3)
            })

    top_matches.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    top_matches = top_matches[:5]

    sorted_scores = sorted(
        similarities.items(),
        key=lambda x:x[1],
        reverse=True
    )

    best_score = sorted_scores[0][1]

    scam_intent_words = [
        "pay",
        "payment",
        "money",
        "transfer",
        "otp",
        "verify",
        "verification",
        "blocked",
        "arrest",
        "police",
        "cbi",
        "ed",
        "cyber",
        "aadhaar",
        "pan",
        "account",
        "bank",
        "fee",
        "charge",
        "claim",
        "prize",
        "investment",
        "profit",
        "loan",
        "urgent",
        "immediately",
        "press one"
    ]

    has_scam_intent = any(
        word in transcript.lower()
        for word in scam_intent_words
    )

    if best_score < 0.60 or not has_scam_intent:
        best_match = "Unknown"
    else:
        best_match = sorted_scores[0][0]

    if len(sorted_scores) > 1:
        runner_up = sorted_scores[1][0]
        runner_up_score = sorted_scores[1][1]
        margin = sorted_scores[0][1] - sorted_scores[1][1]
        
    else:
        runner_up = "None"
        runner_up_score = 0
        margin = best_score

    uncertain = margin < 0.05

    if best_match == "Unknown":
        semantic_similarity = round(best_score, 3)
    else:
        semantic_similarity = similarities[best_match]

    return {
        "predicted_scam": best_match,
        "semantic_similarity": semantic_similarity,
        "semantic_margin": round(margin, 3),
        "uncertain_prediction": uncertain,
        "runner_up": runner_up,
        "runner_up_score": runner_up_score,
        "all_scores": similarities,
        "top_matches": top_matches,
        "evidence_count": len(top_matches),
        "average_similarity": round( sum( m["similarity"] for m in top_matches) / len(top_matches), 3),
        "strong_matches": [m for m in top_matches if m["similarity"] >= 0.70]
    }

if __name__ == "__main__":
    text = """
    Hello sir.
    Your Aadhaar card has been involved
    in money laundering.
    Stay on the call.
    """
    print(semantic_analysis(text))