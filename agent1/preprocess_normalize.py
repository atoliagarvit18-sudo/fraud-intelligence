"""
Normalize raw note photos into a standard, flat, upright rectangle.

Why this exists: perceptual hashing and any feature-region matching only
works if every image is framed the same way. Raw phone photos have the note
at different angles, distances, and positions against different backgrounds.
This script finds the note in each photo, corrects perspective, and outputs
a fixed-size crop containing just the note.

Approach:
  1. Convert to grayscale, blur, edge-detect
  2. Find the largest reasonably-rectangular contour (assumed to be the note)
  3. Perspective-warp that contour to a fixed WIDTH x HEIGHT rectangle
  4. Skip images where no plausible note contour is found (log them for review)
"""

import cv2
import numpy as np
import os

OUT_WIDTH, OUT_HEIGHT = 1000, 450  # standard note aspect ratio ~2.2:1

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

    # reject if the found contour is implausibly small (noise) or fills the whole frame (background)
    area_ratio = cv2.contourArea(largest) / img_area
    if area_ratio < 0.08 or area_ratio > 0.98:
        return None

    return largest

def order_points(pts):
    # order as: top-left, top-right, bottom-right, bottom-left
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def warp_note(img, contour):
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = order_points(box)

    dst = np.array([
        [0, 0],
        [OUT_WIDTH - 1, 0],
        [OUT_WIDTH - 1, OUT_HEIGHT - 1],
        [0, OUT_HEIGHT - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(box, dst)
    warped = cv2.warpPerspective(img, M, (OUT_WIDTH, OUT_HEIGHT))

    # if the note came out taller than wide (portrait capture), rotate to landscape
    return warped

def process_folder(src_folder, dest_folder, log_path):
    os.makedirs(dest_folder, exist_ok=True)
    skipped = []
    processed = 0

    for fname in sorted(os.listdir(src_folder)):
        if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        path = os.path.join(src_folder, fname)
        img = cv2.imread(path)
        if img is None:
            skipped.append((fname, "unreadable"))
            continue

        contour = find_note_contour(img)
        if contour is None:
            skipped.append((fname, "no plausible note contour found"))
            continue

        try:
            warped = warp_note(img, contour)
            out_path = os.path.join(dest_folder, fname)
            cv2.imwrite(out_path, warped)
            processed += 1
        except Exception as e:
            skipped.append((fname, f"warp failed: {e}"))

    with open(log_path, 'w') as f:
        f.write(f"Processed: {processed}\nSkipped: {len(skipped)}\n\n")
        for fname, reason in skipped:
            f.write(f"{fname}: {reason}\n")

    return processed, len(skipped)


if __name__ == "__main__":
    # REQUIRES THE FULL DATASET (not shipped in this repo -- see DATA.md).
    # Expects genuine/ and fake/ folders downloaded alongside this script.
    _ROOT = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIRS = [os.path.join(_ROOT, "genuine"), os.path.join(_ROOT, "fake")]
    OUT_ROOT = os.path.join(_ROOT, "normalized")
    LOG_ROOT = os.path.join(_ROOT, "metadata")

    for ROOT in ROOT_DIRS:
        category = os.path.basename(ROOT)  # 'genuine' or 'fake'
        for denom in sorted(os.listdir(ROOT)):
            denom_path = os.path.join(ROOT, denom)
            if not os.path.isdir(denom_path):
                continue
            for sub in sorted(os.listdir(denom_path)):
                sub_path = os.path.join(denom_path, sub)
                if not os.path.isdir(sub_path):
                    continue
                dest = os.path.join(OUT_ROOT, category, denom, sub)
                log = os.path.join(LOG_ROOT, f"normalize_log_{category}_{denom}_{sub}.txt")
                p, s = process_folder(sub_path, dest, log)
                print(f"{category}/₹{denom}/{sub}: processed={p} skipped={s}")
