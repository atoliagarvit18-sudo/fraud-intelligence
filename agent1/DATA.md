# Full Dataset

The full training dataset (~4GB genuine + fake note images across all six
denominations) is not committed to this repo — too large for git.

**You don't need it to use Agent 1** — `models/*.pkl` are already trained
and `inference.py` / `simulate_feed_demo.py` work standalone using the
committed `sample_data/`.

**You only need the full dataset if retraining** (`train_classifiers.py`,
`preprocess_normalize.py`).

Download link: [add your team's shared Google Drive / storage link here]

Expected folder structure once downloaded, placed alongside these scripts:
```
agent1_currency/
├── genuine/<denom>/...
├── fake/<denom>/...
├── normalized/<genuine|fake>/<denom>/...
├── metadata/train_test_split.json
└── (scripts, models/, etc. as already in this repo)
```
