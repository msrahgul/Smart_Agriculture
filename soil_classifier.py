"""
soil_classifier.py
Local soil classifier using an on-device Keras/TensorFlow image model.

Primary path: OpenCV image load + resize to 224x224 + normalize + model.predict + argmax.

Classes (index mapping):
0 = Alluvial soil
1 = Black soil
2 = Clay soil
3 = Red soil
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import cv2
import numpy as np

_MODEL = None


def _resolve_model_path() -> Path:
    """
    Resolve model path, matching the user's requested default name while supporting repo layout.
    """
    env = (os.environ.get("SOIL_MODEL_PATH") or "").strip()
    if env:
        return Path(env)

    base = Path(__file__).resolve().parent
    candidates = [
        base / "soil_classification_model.h5",
        base / "models" / "soil_classification_model.h5",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Default (for error message)
    return candidates[-1]


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    model_path = _resolve_model_path()
    if not model_path.exists():
        raise FileNotFoundError(f"Soil classification model not found at {model_path}")

    # Prefer TensorFlow Keras, fall back to standalone Keras if needed.
    # Some exported models include newer layer configs (e.g., DepthwiseConv2D `groups`).
    # Patch-load by ignoring unsupported config keys when possible.
    try:
        import tensorflow as tf  # type: ignore
        from tensorflow.keras.models import load_model  # type: ignore

        class _PatchedDepthwiseConv2D(tf.keras.layers.DepthwiseConv2D):  # type: ignore
            @classmethod
            def from_config(cls, config):  # type: ignore
                config = dict(config or {})
                config.pop("groups", None)
                return super().from_config(config)

        _MODEL = load_model(
            str(model_path),
            compile=False,
            custom_objects={
                "DepthwiseConv2D": _PatchedDepthwiseConv2D,
            },
        )
    except Exception:
        from keras.models import load_model  # type: ignore

        _MODEL = load_model(str(model_path), compile=False)
    print(f"[soil_classifier] ML model loaded from {model_path}")
    return _MODEL


def classify_soil(image_path: str) -> str:
    # Match user's mapping exactly.
    soil_types: Dict[int, str] = {
        0: "Alluvial soil",
        1: "Black soil",
        2: "Clay soil",
        3: "Red soil",
    }

    model = _load_model()
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
    img = img.astype("float32") / 255.0
    img = np.expand_dims(img, axis=0)

    preds = model.predict(img, verbose=0)
    predicted_class_index = int(np.argmax(preds, axis=1)[0])
    label = soil_types.get(predicted_class_index, "Unknown Soil Type")
    print(f"[soil_classifier] ML classified: {label} (idx={predicted_class_index})")
    return label
