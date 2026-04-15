"""
soil_classifier.py
Local soil classifier with no external API dependency.

Uses color statistics from the uploaded image to classify one of:
Alluvial soil / Black soil / Clay soil / Red soil.
"""

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


def classify_soil(image_path: str) -> str:
    """
    Classify soil type from an image path.

    Uses local pixel-statistics heuristics only.
    """
    result = _heuristic_classify(image_path)
    print(f"[soil_classifier] Heuristic classified: {result}")
    return result
