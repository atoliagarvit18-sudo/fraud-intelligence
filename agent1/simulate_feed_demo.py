"""
Phase 6 — Simulated live feed demo.

Simulates a bank camera/scanner feed: processes a folder of note images
one at a time (with a short delay, standing in for real-time capture),
running each through the full Agent 1 pipeline, and builds a circulation
map of detected fake-note batches across assigned demo locations.

No human uploads anything during this loop -- it walks a pre-staged
folder exactly as a live camera feed would deliver frames.
"""
import os
import sys
import time
import json
import random

sys.path.insert(0, os.path.dirname(__file__))
from inference import process_note_image

DATASET_ROOT = os.path.dirname(os.path.abspath(__file__))

# Assigned demo locations (Rajasthan region, matching the original pitch's
# Jaipur/Jodhpur narrative) -- notes are randomly assigned one of these per
# detection, simulating different bank branches reporting in.
DEMO_LOCATIONS = [
    {"name": "Jaipur Branch A", "coords": [26.9124, 75.7873]},
    {"name": "Jaipur Branch B", "coords": [26.8850, 75.8200]},
    {"name": "Jodhpur Branch A", "coords": [26.2389, 73.0243]},
    {"name": "Ajmer Branch A", "coords": [26.4499, 74.6399]},
]


def simulate_feed(image_paths, denom_hints=None, delay_seconds=0.0, max_images=None):
    """
    image_paths: list of file paths to process in order (the "feed").
    denom_hints: optional list matching image_paths, one denom per image
                 (if None, auto-detection is used for every frame).
    delay_seconds: pause between frames to simulate real-time arrival.
    """
    if max_images:
        image_paths = image_paths[:max_images]
        if denom_hints:
            denom_hints = denom_hints[:max_images]

    detections = []
    for i, path in enumerate(image_paths):
        location = random.choice(DEMO_LOCATIONS)
        hint = denom_hints[i] if denom_hints else None

        result = process_note_image(
            path, denom_hint=hint,
            location=location["name"],
        )
        result["location_coords"] = location["coords"]
        detections.append(result)

        status_line = f"[{i+1}/{len(image_paths)}] {os.path.basename(path)[:40]:<42} -> {result['status']}"
        if result.get("verdict"):
            status_line += f" | {result['verdict']} (conf={result['confidence']})"
        if result.get("batch_id"):
            status_line += f" | {result['batch_id']}" + (" (NEW)" if result["is_new_batch"] else "")
        print(status_line)

        if delay_seconds:
            time.sleep(delay_seconds)

    return detections


def build_circulation_map(detections, output_path):
    try:
        import folium
    except ImportError:
        print("[INFO] folium module not installed — skipping HTML circulation map generation.")
        return None

    fake_detections = [d for d in detections if d.get("verdict") == "fake"]
    if not fake_detections:
        print("No fake detections to map.")
        return None

    avg_lat = sum(d["location_coords"][0] for d in fake_detections) / len(fake_detections)
    avg_lon = sum(d["location_coords"][1] for d in fake_detections) / len(fake_detections)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=9)

    batch_colors = {}
    palette = ["red", "orange", "purple", "darkred", "cadetblue", "darkgreen"]

    for d in fake_detections:
        batch_id = d["batch_id"]
        if batch_id not in batch_colors:
            batch_colors[batch_id] = palette[len(batch_colors) % len(palette)]
        color = batch_colors[batch_id]

        popup_text = (f"{d['location']}<br>"
                      f"Denomination: ₹{d['denomination']}<br>"
                      f"Confidence: {d['confidence']}<br>"
                      f"Batch: {batch_id}<br>"
                      f"Time: {d['timestamp']}")

        folium.CircleMarker(
            location=d["location_coords"],
            radius=8,
            popup=popup_text,
            color=color,
            fill=True,
            fill_opacity=0.7
        ).add_to(m)

    m.save(output_path)
    print(f"\nCirculation map saved to {output_path}")
    print(f"Batches detected: {len(batch_colors)}")
    return m


def run_demo():
    # Build a mixed feed from the small committed sample_data/ folder.
    # (For a larger/real demo, point feed_paths at your own image folder --
    # the pipeline doesn't care about the source, just the file paths.)
    sample_dir = os.path.join(DATASET_ROOT, "sample_data")
    feed_paths = []
    feed_hints = []

    for fname in sorted(os.listdir(sample_dir)):
        if "_fake_" in fname or "_genuine_" in fname:
            denom = fname.split("_")[0]
            feed_paths.append(os.path.join(sample_dir, fname))
            feed_hints.append(denom)

    print(f"=== Agent 1 Simulated Feed Demo ===")
    print(f"Processing {len(feed_paths)} images across denominations {set(feed_hints)}\n")

    detections = simulate_feed(feed_paths, denom_hints=feed_hints, delay_seconds=0)

    print(f"\n=== Summary ===")
    n_fake = sum(1 for d in detections if d.get("verdict") == "fake")
    n_genuine = sum(1 for d in detections if d.get("verdict") == "genuine")
    n_errors = sum(1 for d in detections if d.get("status", "").startswith("error"))
    print(f"Total processed: {len(detections)}")
    print(f"Flagged fake: {n_fake}, Flagged genuine: {n_genuine}, Errors: {n_errors}")

    output_path = os.path.join(DATASET_ROOT, "agent1_demo_circulation_map.html")
    build_circulation_map(detections, output_path)

    with open(os.path.join(DATASET_ROOT, "demo_run_detections.json"), 'w') as f:
        json.dump(detections, f, indent=2)

    return detections


if __name__ == "__main__":
    run_demo()
