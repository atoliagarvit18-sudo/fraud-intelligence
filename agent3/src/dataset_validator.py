def validate_example(example, scam_type):

    if not isinstance(example, dict):
        return False

    if "type" not in example:
        return False

    if "text" not in example:
        return False

    if example["type"] != scam_type:
        return False

    text = example["text"].strip()

    if len(text) == 0:
        return False

    words = text.split()

    if len(words) < 8:
        return False

    if len(words) > 40:
        return False

    banned = [
        "lorem ipsum",
        "example",
        "sample",
        "test message",
        "dummy"
    ]

    lower = text.lower()

    for word in banned:
        if word in lower:
            return False

    return True