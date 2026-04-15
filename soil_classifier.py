"""
soil_classifier.py
Local soil classifier only (no Gemini dependency).

Classifies soil image into one of:
- Alluvial soil
- Black soil
- Clay soil
- Red soil
"""

from PIL import Image
import numpy as np

_CLASS_NAMES = ["Alluvial soil", "Black soil", "Clay soil", "Red soil"]


def _heuristic_classify(image_path: str) -> str:
    """
    Classify soil from dominant pixel color statistics.
    No external API required.
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    # Use center crop to reduce background noise
    margin_x, margin_y = int(w * 0.2), int(h * 0.2)
    img = img.crop((margin_x, margin_y, w - margin_x, h - margin_y))
    img = img.resize((128, 128))

    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    mean_r = float(np.mean(r))
    mean_g = float(np.mean(g))
    mean_b = float(np.mean(b))
    mean_brightness = (mean_r + mean_g + mean_b) / 3.0

    redness = mean_r / max(mean_b, mean_g, 1.0)
    greenishness = mean_g / max(mean_r, mean_b, 1.0)
    darkness = 1.0 - (mean_brightness / 255.0)

    if darkness > 0.65:
        return "Black soil"

    if redness > 1.35 and mean_r > 100:
        return "Red soil"

    if mean_brightness > 130 and redness < 1.35 and greenishness < 1.1:
        return "Alluvial soil"

    if mean_brightness < 130 and darkness < 0.65:
        return "Clay soil"

    scores = {
        "Red soil": redness,
        "Black soil": darkness,
        "Alluvial soil": 1.0 / max(abs(redness - 1.0) + 0.01, 0.01),
        "Clay soil": greenishness,
    }
    return max(scores, key=scores.get)


def classify_soil(image_path: str) -> str:
    """
    Classify soil type from an image path using only local logic.
    """
    result = _heuristic_classify(image_path)
    print(f"[soil_classifier] Local heuristic classified: {result}")
    return result