"""
ml_models.py – Prediction helper for yield and pest risk ML models.
Loads trained scikit-learn pipelines from the models/ directory.
"""
from pathlib import Path
import pandas as pd
import joblib

YIELD_MODEL_PATH   = Path("models/yield_model.pkl")
PEST_MODEL_PATH    = Path("models/pest_risk_model.pkl")
PEST_ENCODER_PATH  = Path("models/pest_label_encoder.pkl")

_yield_model   = None
_pest_model    = None
_pest_encoder  = None
_models_loaded = False


def load_models():
    """Load all trained ML models from disk. Call once at startup."""
    global _yield_model, _pest_model, _pest_encoder, _models_loaded

    if _yield_model is None:
        if YIELD_MODEL_PATH.exists():
            _yield_model = joblib.load(YIELD_MODEL_PATH)
            print(f"[ml_models] Yield model loaded from {YIELD_MODEL_PATH}")
        else:
            print(f"[ml_models] WARNING: Yield model not found at {YIELD_MODEL_PATH}. Run train_yield_model.py")

    if _pest_model is None:
        if PEST_MODEL_PATH.exists():
            _pest_model = joblib.load(PEST_MODEL_PATH)
            print(f"[ml_models] Pest risk model loaded from {PEST_MODEL_PATH}")
        else:
            print(f"[ml_models] WARNING: Pest model not found at {PEST_MODEL_PATH}. Run train_pest_risk_model.py")

    if _pest_encoder is None:
        if PEST_ENCODER_PATH.exists():
            _pest_encoder = joblib.load(PEST_ENCODER_PATH)

    _models_loaded = True


def predict_yield(input_dict: dict) -> float:
    """
    Predict crop yield (t/ha) from a feature dict representing one row
    of the TamilNadu_ML_Master_Historical dataset.
    """
    if _yield_model is None:
        load_models()
    if _yield_model is None:
        raise FileNotFoundError(
            "Yield model not found. Run: python train_yield_model.py"
        )
    df = pd.DataFrame([input_dict])
    pred = _yield_model.predict(df)[0]
    return float(pred)


def predict_pest_risk(input_dict: dict) -> str:
    """
    Predict pest risk label (Low / Medium / High) from a feature dict.
    """
    if _pest_model is None:
        load_models()
    if _pest_model is None or _pest_encoder is None:
        raise FileNotFoundError(
            "Pest risk model not found. Run: python train_pest_risk_model.py"
        )
    df = pd.DataFrame([input_dict])
    pred_encoded = _pest_model.predict(df)[0]
    label = _pest_encoder.inverse_transform([pred_encoded])[0]
    return str(label)


def models_available() -> dict:
    """Return which models are currently loaded."""
    return {
        "yield_model":    _yield_model is not None,
        "pest_risk_model": _pest_model is not None,
    }
