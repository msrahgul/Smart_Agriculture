"""
soil_classifier.py
Multi-strategy soil classifier (no TensorFlow dependency):

  Strategy 1 — Gemini Vision (best): Sends image to Gemini 1.5 Flash Vision API.
               Returns one of: Alluvial soil / Black soil / Clay soil / Red soil.
  Strategy 2 — Heuristic (fallback): HSL color-space analysis of the soil image.
               Uses dominant hue/saturation/lightness to classify soil type.
"""

import os
from pathlib import Path
import numpy as np
from PIL import Image

_CLASS_NAMES = ["Alluvial soil", "Black soil", "Clay soil", "Red soil"]

# ── Heuristic thresholds (based on typical soil RGB signatures) ──────────────
# Red soil: high red channel, warm hue
# Black soil: all channels low (dark)
# Alluvial soil: medium brown, grayish
# Clay soil: olive/gray-brown, moderate values

def _heuristic_classify(image_path: str) -> str:
    """
    Classify soil from dominant pixel color statistics.
    No ML model required — uses HSL statistics of the centre crop.
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    # Use centre 60% crop to avoid edge noise
    margin_x, margin_y = int(w * 0.2), int(h * 0.2)
    img = img.crop((margin_x, margin_y, w - margin_x, h - margin_y))
    img = img.resize((128, 128))

    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    mean_r = float(np.mean(r))
    mean_g = float(np.mean(g))
    mean_b = float(np.mean(b))
    mean_brightness = (mean_r + mean_g + mean_b) / 3.0

    # Compute redness: how dominant red channel is
    redness      = mean_r / max(mean_b, mean_g, 1.0)
    # Compute greenishness
    greenishness = mean_g / max(mean_r, mean_b, 1.0)
    # Darkness (0=black, 255=white)
    darkness     = 1.0 - (mean_brightness / 255.0)

    # ── Decision rules ────────────────────────────────────────────────────────
    # Black soil: very dark overall, all channels low
    if darkness > 0.65:
        return "Black soil"

    # Red soil: significantly red-dominated, medium brightness
    if redness > 1.35 and mean_r > 100:
        return "Red soil"

    # Alluvial soil: moderate brightness, balanced channels, slight reddish-brown
    if mean_brightness > 130 and redness < 1.35 and greenishness < 1.1:
        return "Alluvial soil"

    # Clay soil: olive/darker grey-brown, lower brightness but not black
    if mean_brightness < 130 and darkness < 0.65:
        return "Clay soil"

    # Final fallback: pick by strongest channel signal
    scores = {
        "Red soil": redness,
        "Black soil": darkness,
        "Alluvial soil": 1.0 / max(abs(redness - 1.0) + 0.01, 0.01),
        "Clay soil": greenishness,
    }
    return max(scores, key=scores.get)


def _gemini_classify(image_path: str) -> str | None:
    """
    Use Gemini Vision to classify the soil image.
    Returns one of the four soil classes, or None if unavailable.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
        from google.generativeai import protos

        genai.configure(api_key=api_key)

        model = genai.GenerativeModel("gemini-1.5-flash")

        # Read image bytes
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        # Determine mime type
        ext = Path(image_path).suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        prompt = (
            "You are an agricultural soil expert. Look at this soil image and classify it "
            "into EXACTLY ONE of these four categories:\n"
            "- Alluvial soil\n"
            "- Black soil\n"
            "- Clay soil\n"
            "- Red soil\n\n"
            "Respond with ONLY the soil type name, nothing else. "
            "Example response: Red soil"
        )

        response = model.generate_content([
            prompt,
            protos.Part(inline_data=protos.Blob(mime_type=mime_type, data=img_bytes))
        ])

        answer = response.text.strip()

        # Validate answer is one of our classes
        for cls in _CLASS_NAMES:
            if cls.lower() in answer.lower():
                return cls

        return None  # Unexpected response — fall back to heuristic

    except Exception as e:
        print(f"[soil_classifier] Gemini Vision failed: {e}. Using heuristic fallback.")
        return None


def classify_soil(image_path: str) -> str:
    """
    Classify soil type from an image path.

    Tries Gemini Vision first (most accurate), falls back to
    pixel-statistics heuristic if Gemini is unavailable or fails.
    """
    # Strategy 1: Gemini Vision
    result = _gemini_classify(image_path)
    if result:
        print(f"[soil_classifier] Gemini Vision classified: {result}")
        return result

    # Strategy 2: Heuristic fallback
    result = _heuristic_classify(image_path)
    print(f"[soil_classifier] Heuristic classified: {result}")
    return result
