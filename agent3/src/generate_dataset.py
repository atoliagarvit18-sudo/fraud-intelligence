import json
import os
from pathlib import Path
from dataset_validator import validate_example
from dotenv import load_dotenv
from groq import Groq
from semantic_deduplicator import remove_semantic_duplicates

# ----------------------------
# Load API Key
# ----------------------------

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise Exception("GROQ_API_KEY not found.")

client = Groq(api_key=api_key)

# ----------------------------
# Scam Types
# ----------------------------

SCAM_TYPES = {
    "1": ("Digital Arrest", "digital_arrest.json"),
    "2": ("Bank Fraud", "bank_fraud.json"),
    "3": ("KYC Scam", "kyc.json"),
    "4": ("Courier Scam", "courier.json"),
    "5": ("Investment Scam", "investment.json"),
    "6": ("Lottery Scam", "lottery.json"),
    "7": ("Job Scam", "job.json"),
}

def generate_examples(scam_type, count):

    prompt = f"""
You are creating a high-quality training dataset for an Indian scam-call detection AI.

Generate EXACTLY {count} UNIQUE examples.

Scam category:
{scam_type}

IMPORTANT:
Every example MUST belong ONLY to the category "{scam_type}".

If the category is Digital Arrest, examples MUST involve one or more of:

- Police
- CBI
- ED
- Cyber Crime
- Customs
- Narcotics
- Money Laundering
- Illegal Parcel
- Aadhaar
- PAN
- Arrest
- FIR
- Video Verification
- Stay on the Call
- Investigation
- Warrant
- Identity Misuse

DO NOT generate:

- Tech support scams
- Microsoft scams
- Credit card scams
- Lottery scams
- Investment scams
- OTP scams
- Banking scams

Each example should sound like something a scammer would actually say.

Return ONLY a JSON array.

Format:

[
    {{
        "type":"{scam_type}",
        "text":"..."
    }}
]

No markdown.

No explanations.

No numbering.

Only JSON.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.8,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content
    text = (content or "").strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)

def save_examples(filename, new_examples):

    knowledge_dir = Path(__file__).parent / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)

    file_path = knowledge_dir / filename

    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = []

    new_examples = remove_semantic_duplicates(
       existing,
        new_examples
    )

    existing_texts = {
        item["text"].strip().lower()
        for item in existing
    }

    added = 0

    for example in new_examples:
        
        if not validate_example(example, example["type"]):
            continue
        
        text = example["text"].strip()

        if text.lower() not in existing_texts:
            existing.append(example)
            existing_texts.add(text.lower())
            added += 1

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

    return added, len(existing)

print("=" * 50)
print("Knowledge Base Generator")
print("=" * 50)

for key, value in SCAM_TYPES.items():
    print(f"{key}. {value[0]}")

choice = input("\nChoice: ").strip()

if choice not in SCAM_TYPES:
    raise Exception("Invalid choice.")

count = int(input("Number of examples: "))

scam_name, filename = SCAM_TYPES[choice]

print(f"\nGenerating {count} examples...\n")

BATCH_SIZE = 25

remaining = count
batch = 1

while remaining > 0:

    current_batch = min(BATCH_SIZE, remaining)

    print(f"\nBatch {batch}")

    try:

        examples = generate_examples(
            scam_name,
            current_batch
        )

        added, total = save_examples(
            filename,
            examples
        )

        print(f"Generated : {len(examples)}")
        print(f"Added     : {added}")
        print(f"Skipped   : {len(examples)-added}")
        print(f"Total     : {total}")

        if added > 0:
            remaining -= added

        else:
            print("No new examples added, retrying...")
            
            if batch > 5:
                print("Too many failed attempts. Stopping.")
                break

        batch += 1

    except Exception as e:

        print("Batch failed")
        print(e)

print("\n===================================")
print("Dataset generation completed.")
print("===================================")