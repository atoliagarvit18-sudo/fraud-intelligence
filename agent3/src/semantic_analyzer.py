from sentence_transformers import SentenceTransformer, util

print("Loading Semantic Model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

SCAM_EXAMPLES = {
    "Digital Arrest": [
        "Your Aadhaar has been linked to illegal activities.",
        "This is CBI speaking.",
        "This is the ED department.",
        "Customs department speaking.",
        "Your parcel contains drugs.",
        "Money laundering case has been registered.",
        "Stay on the video call.",
        "Cyber crime department speaking.",
        "Press one to connect to an officer.",
        "Transfer money for verification."
    ],

    "Bank Fraud": [
        "Tell me your OTP.",
        "Share your debit card number.",
        "Provide your CVV.",
        "Your bank account will be blocked.",
        "Verify your bank account.",
        "Complete your banking verification.",
        "Share your UPI PIN.",
        "Confirm your account details."
    ],

    "KYC Scam": [
        "Your KYC has expired.",
        "Update your KYC immediately.",
        "Install this application.",
        "Download this APK.",
        "Complete your account verification.",
        "Verify your PAN card.",
        "Click this link.",
        "Your SIM will be blocked."
    ]
}

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

    for scam, embeddings in pattern_embeddings.items():

        scores = util.cos_sim(
            transcript_embedding,
            embeddings
        )[0]

        similarities[scam] = round(float(scores.max()), 3)

    best_match = max(similarities, key=similarities.get)

    best_score = similarities[best_match]

    sorted_scores = sorted(
        similarities.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "predicted_scam": best_match,
        "semantic_similarity": best_score,
        "runner_up": sorted_scores[1][0],
        "runner_up_score": sorted_scores[1][1],
        "all_scores": similarities
    }

if __name__ == "__main__":

    text = """
    Hello sir.
    Your Aadhaar card has been involved
    in money laundering.
    Stay on the call.
    """

    print(semantic_analysis(text))