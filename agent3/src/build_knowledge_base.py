import json
from pathlib import Path

knowledge_dir = Path(__file__).parent / "knowledge"

files = [
    "digital_arrest.json",
    "bank_fraud.json",
    "kyc.json",
    "courier.json",
    "investment.json",
    "lottery.json",
    "job.json"
]

knowledge_base = []

for filename in files:

    path = knowledge_dir / filename

    if not path.exists():
        print(f"Skipping {filename}")
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    knowledge_base.extend(data)

output_path = knowledge_dir / "knowledge_base.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(
        knowledge_base,
        f,
        indent=4,
        ensure_ascii=False
    )

print(f"Knowledge Base Built Successfully!")
print(f"Total Examples : {len(knowledge_base)}")