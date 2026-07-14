
# Agent 1 — Currency Intelligence Agent

Computer-vision agent for the multi-agent fraud detection system. Detects
counterfeit Indian currency notes, fingerprints flagged fakes, and clusters
them into likely printing batches for geographic circulation tracking.

## What it does

1. Takes a photo of a currency note (any angle/background)
2. Deskews and crops it via OpenCV
3. Auto-detects denomination, classifies real/fake per denomination
4. Fingerprints flagged fakes (perceptual hashing) and matches against
   previously seen fakes to detect batches

5. Outputs a structured JSON result for the orchestrator to consume

## Setup

```bash
pip install -r requirements.txt
```

## Usage — calling Agent 1 from the orchestrator

```python
from agents.agent1_currency.inference import process_note_image

result = process_note_image(
    image_path="path/to/note.jpg",
    denom_hint=None,          # optional; auto-detected if not given
    location="Jaipur_Branch_A"
)
```

### Output schema

```json
{
  "image_path": "str",
  "timestamp": "ISO 8601 str",
  "location": "str or null",
  "status": "ok | error_unreadable_image | error_no_note_detected | error_denomination_unknown | error_no_model_for_denomination | flagged_low_denomination_confidence",
  "denomination": "str (e.g. '500') or null",
  "denomination_confidence": "float 0-1, only present if auto-detected",
  "denomination_auto_detected": "bool",
  "verdict": "'genuine' | 'fake' | null (null if status != ok)",
  "confidence": "float 0-1 or null",
  "batch_id": "str (e.g. 'batch_003') or null, only present if verdict == 'fake'",
  "is_new_batch": "bool or null"
}
```

**Orchestrator integration note:** treat `status != "ok"` as "no usable
verdict this frame" rather than an exception — these are expected outcomes
(bad photo, unreadable image), not bugs. `flagged_low_denomination_confidence`
means the result is provisional; the orchestrator should weight it lower or
skip correlating on it.

## Running the demo

```bash
python simulate_feed_demo.py
```

Processes `sample_data/` as a simulated live feed and outputs
`agent1_demo_circulation_map.html`.

## Known limitations (read before demo day)

- **Model accuracy** (fixed as of this version — see below):

  | Denom | Accuracy |
  |---|---|
  | ₹10 | 97% |
  | ₹20 | 87% |
  | ₹50 | 85% |
  | ₹100 | 89% |
  | ₹200 | 72% |
  | ₹500 | 83% |

  These came from fixing two real bugs: (1) the train/test split had
  accidentally put an entire genuine-note photo source (~100 images)
  wholly into the test set with zero representation in training — this
  also means the previous "₹200 = 89%" number was itself inflated by the
  same bug, now correctly showing 72%; (2) the original classical features
  (color histograms + edge density) were too weak — adding a Local Binary
  Pattern texture histogram (currency security print is fundamentally a
  texture signal) was the single biggest accuracy contributor across every
  denomination.
- **Denomination auto-detection is ~53% accurate** (6-class). Results below
  45% confidence are flagged `flagged_low_denomination_confidence` — don't
  silently trust these.
- **Batch clustering works reliably only on consistently-oriented images.**
  On diverse real-world photo angles it under-clusters. Verified working
  correctly for exact re-scans of the same note. Full explanation in
  `docs/capabilities_and_roadmap.md`.
- Full dataset (4GB+) is not in this repo — see `DATA.md` for the download
  link if you need to retrain.

## File guide

| File | Purpose |
|---|---|
| `inference.py` | The callable interface — orchestrator imports this |
| `simulate_feed_demo.py` | Demo entry point for the live-feed simulation |
| `train_classifiers.py` | Retrains the six denomination classifiers |
| `models/*.pkl` | Trained classifiers + denomination detector |
| `notebooks/agent1_pipeline.ipynb` | Full phase-by-phase build walkthrough |
