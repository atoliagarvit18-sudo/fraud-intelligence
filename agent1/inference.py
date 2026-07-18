"""
Agent 1 — unified inference pipeline.

Single entry point: raw note image in -> structured detection result out.
This is what the orchestrator (or the simulated demo feed) calls per image.

Ties together:
  Phase 2 (preprocessing/normalization)
  Phase 3 (per-denomination classifier)
  Phase 5 (perceptual hash fingerprinting + batch clustering)
"""
import os
import sys
import cv2
import numpy as np
import pickle
import json
import imagehash
from PIL import Image
from datetime import datetime

try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except AttributeError:
    pass

DATASET_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_ROOT = os.path.join(DATASET_ROOT, "models")
OUT_WIDTH, OUT_HEIGHT = 1000, 450

# ---- Phase 2: preprocessing ----

def find_note_contour(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    img_area = img.shape[0] * img.shape[1]
    largest = max(contours, key=cv2.contourArea)
    area_ratio = cv2.contourArea(largest) / img_area
    if area_ratio < 0.08 or area_ratio > 0.98:
        return None
    return largest

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def normalize_note(img):
    """Returns the deskewed/cropped note, or None if no note found."""
    contour = find_note_contour(img)
    if contour is None:
        return None
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = order_points(box)
    dst = np.array([[0, 0], [OUT_WIDTH-1, 0], [OUT_WIDTH-1, OUT_HEIGHT-1], [0, OUT_HEIGHT-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(box, dst)
    return cv2.warpPerspective(img, M, (OUT_WIDTH, OUT_HEIGHT))


# ---- Phase 3: feature extraction + classification ----

def lbp_histogram(gray, n_bins=32):
    h, w = gray.shape
    center = gray[1:-1, 1:-1]
    code = np.zeros_like(center, dtype=np.uint8)
    offsets = [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]
    for i, (dy, dx) in enumerate(offsets):
        neighbor = gray[1+dy:h-1+dy, 1+dx:w-1+dx]
        code |= ((neighbor >= center).astype(np.uint8) << i)
    hist, _ = np.histogram(code, bins=n_bins, range=(0, 256))
    return hist / (hist.sum() + 1e-6)


def extract_features(img):
    img = cv2.resize(img, (300, 135))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    features = []
    for ch in range(3):
        hist = cv2.calcHist([img], [ch], None, [32], [0, 256]).flatten()
        features.extend(hist / (hist.sum() + 1e-6))
    for ch in range(3):
        hist = cv2.calcHist([hsv], [ch], None, [16], [0, 256]).flatten()
        features.extend(hist / (hist.sum() + 1e-6))
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    mag, ang = cv2.cartToPolar(gx, gy)
    hog_hist, _ = np.histogram(ang, bins=9, range=(0, 2*np.pi), weights=mag)
    features.extend((hog_hist / (hog_hist.sum() + 1e-6)).tolist())
    h, w = gray.shape
    for by in range(3):
        for bx in range(5):
            block = gray[by*h//3:(by+1)*h//3, bx*w//5:(bx+1)*w//5]
            features.append(block.mean() / 255.0)
            features.append(block.std() / 255.0)
    features.append(gray.std() / 255.0)
    features.append(gray.mean() / 255.0)
    features.append(cv2.Canny(gray, 50, 150).mean() / 255.0)
    features.extend(lbp_histogram(gray).tolist())
    return np.array(features).reshape(1, -1)

_MODEL_CACHE = {}

def load_model(denom):
    if denom not in _MODEL_CACHE:
        path = os.path.join(MODELS_ROOT, f"{denom}_classifier.pkl")
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            _MODEL_CACHE[denom] = pickle.load(f)
    return _MODEL_CACHE[denom]

_DENOM_MODEL_CACHE = {}

def load_denomination_model():
    if 'model' not in _DENOM_MODEL_CACHE:
        path = os.path.join(MODELS_ROOT, "denomination_classifier.pkl")
        if not os.path.exists(path):
            _DENOM_MODEL_CACHE['model'] = None
        else:
            with open(path, 'rb') as f:
                _DENOM_MODEL_CACHE['model'] = pickle.load(f)
    return _DENOM_MODEL_CACHE['model']

DENOM_CONFIDENCE_THRESHOLD = 0.45  # below this, flag for manual review rather than trust the guess

def detect_denomination(normalized_img):
    """Returns (denom, confidence). Denom classifier is weak (~53% accuracy,
    6-class) -- this is a known limitation, not treated as ground truth."""
    model = load_denomination_model()
    if model is None:
        return None, 0.0
    features = extract_features(normalized_img)
    pred = model.predict(features)[0]
    proba = model.predict_proba(features)[0]
    confidence = float(max(proba))
    return pred, confidence


# ---- Phase 5: fingerprinting + batch clustering ----

_KNOWN_FAKE_FINGERPRINTS = []  # list of (hash, detection_record)
CLUSTER_THRESHOLD = 12

def fingerprint(normalized_img):
    pil_img = Image.fromarray(cv2.cvtColor(normalized_img, cv2.COLOR_BGR2RGB))
    return imagehash.phash(pil_img, hash_size=16)

def match_batch(note_hash):
    """Compare against known fake fingerprints; return matched batch id or None."""
    for known_hash, record in _KNOWN_FAKE_FINGERPRINTS:
        if note_hash - known_hash <= CLUSTER_THRESHOLD:
            return record['batch_id']
    return None

def register_fake(note_hash, location, timestamp):
    batch_id = match_batch(note_hash)
    is_new_batch = batch_id is None
    if is_new_batch:
        batch_id = f"batch_{len(set(r['batch_id'] for _, r in _KNOWN_FAKE_FINGERPRINTS)) + 1:03d}"
    record = {"batch_id": batch_id, "location": location, "timestamp": timestamp}
    _KNOWN_FAKE_FINGERPRINTS.append((note_hash, record))
    return batch_id, is_new_batch


# ---- Unified pipeline ----

def process_note_image(image_path, denom_hint=None, location=None, timestamp=None):
    """
    Full Agent 1 pipeline on one image.
    denom_hint: if known (e.g. from a denomination pre-classifier or manual
                tag), skips denomination detection. Required in this version
                since we don't yet have a denomination classifier -- see
                'known limitations' in the accompanying report.
    Returns a structured result dict.
    """
    timestamp = timestamp or datetime.now().isoformat()
    result = {
        "image_path": image_path,
        "timestamp": timestamp,
        "location": location,
        "status": None,
        "denomination": denom_hint,
        "verdict": None,
        "confidence": None,
        "batch_id": None,
        "is_new_batch": None,
    }

    img = cv2.imread(image_path)
    if img is None:
        result["status"] = "error_unreadable_image"
        return result

    normalized = normalize_note(img)
    if normalized is None:
        result["status"] = "error_no_note_detected"
        return result

    if denom_hint is None:
        detected_denom, denom_confidence = detect_denomination(normalized)
        if detected_denom is None:
            result["status"] = "error_denomination_unknown"
            return result
        result["denomination"] = detected_denom
        result["denomination_confidence"] = round(denom_confidence, 3)
        result["denomination_auto_detected"] = True
        if denom_confidence < DENOM_CONFIDENCE_THRESHOLD:
            result["status"] = "flagged_low_denomination_confidence"
            result["note"] = ("Denomination auto-detection confidence is low; "
                               "this result should be treated as provisional, "
                               "not routed to automated action without review.")
        denom_hint = detected_denom
    else:
        result["denomination_auto_detected"] = False

    model = load_model(denom_hint)
    if model is None:
        result["status"] = "error_no_model_for_denomination"
        return result

    features = extract_features(normalized)
    pred = model.predict(features)[0]
    proba = model.predict_proba(features)[0]
    confidence = float(proba[pred])

    result["verdict"] = "fake" if pred == 1 else "genuine"
    result["confidence"] = round(confidence, 3)
    result["status"] = "ok"

    if pred == 1:
        note_hash = fingerprint(normalized)
        batch_id, is_new = register_fake(note_hash, location, timestamp)
        result["batch_id"] = batch_id
        result["is_new_batch"] = is_new

    return result


if __name__ == "__main__":
    # smoke test using the small committed sample_data/ folder
    sample_dir = os.path.join(DATASET_ROOT, "sample_data")
    sample_files = sorted(f for f in os.listdir(sample_dir) if "500" in f)

    print("Running smoke test on sample_data/ (denom_hint provided)...\n")
    for fname in sample_files:
        path = os.path.join(sample_dir, fname)
        result = process_note_image(path, denom_hint="500", location="Jaipur_Branch_A")
        print(json.dumps(result, indent=2))
        print()

    print("\n--- Now with auto denomination detection (no hint given) ---\n")
    for fname in sample_files[:2]:
        path = os.path.join(sample_dir, fname)
        result = process_note_image(path, denom_hint=None, location="Jaipur_Branch_A")
        print(json.dumps(result, indent=2))
        print()
