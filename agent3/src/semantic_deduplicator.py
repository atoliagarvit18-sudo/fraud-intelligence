from sentence_transformers import SentenceTransformer, util


print("Loading duplicate detection model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def remove_semantic_duplicates(
        existing,
        new_examples,
        threshold=0.92
):

    if len(existing) == 0:
        return new_examples

    existing_texts = [
        item["text"]
        for item in existing
    ]

    existing_embeddings = model.encode(
        existing_texts,
        convert_to_tensor=True
    )

    accepted = []

    for item in new_examples:

        text = item["text"]

        embedding = model.encode(
            text,
            convert_to_tensor=True
        )

        scores = util.cos_sim(
            embedding,
            existing_embeddings
        )[0]

        highest = float(
            scores.max()
        )

        if highest < threshold:
            accepted.append(item)

        else:
            print(
                "Skipped similar:",
                text
            )

    return accepted