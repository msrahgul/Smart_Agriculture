"""
app.py – Smart Farming AI Agent: Flask Server
"""

from flask import Flask, request, jsonify, render_template
import os
import uuid
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np

import data_engine as de
import agent
import ml_models
import nlg

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB max upload

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# In-memory conversation history: {session_id: [{"role": "...", ...}]}
conversation_store: dict = {}

# Load data and models at startup
de.load_data()
ml_models.load_models()

# Soil classifier cache
_classify_soil = None


def allowed_image_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def _load_soil_classifier():
    """
    Load and warm up the soil classifier once at startup.
    """
    global _classify_soil
    try:
        from soil_classifier import classify_soil
        _classify_soil = classify_soil

        # Real warm-up using a temporary blank image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = tmp.name

        try:
            dummy = np.zeros((224, 224, 3), dtype=np.uint8)
            Image.fromarray(dummy).save(temp_path)
            _classify_soil(temp_path)
            print("[app] Soil classifier loaded and warmed up.")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        print(f"[app] WARNING: Soil classifier could not be loaded: {e}")
        _classify_soil = None


def _get_soil_classifier():
    return _classify_soil


def _trim_history(history: list, limit: int = 50) -> list:
    return history[-limit:] if len(history) > limit else history


# Load immediately
_load_soil_classifier()


@app.route("/")
def index():
    return render_template("index.html", districts=de.ALL_DISTRICTS)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "district_count": len(de.ALL_DISTRICTS),
        "yield_model_loaded": ml_models.models_available()["yield_model"],
        "pest_model_loaded": ml_models.models_available()["pest_risk_model"],
        "soil_classifier_loaded": _get_soil_classifier() is not None,
    })


@app.route("/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint. Accepts JSON: {message, session_id}
    """
    print("[app] Received /chat request")
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    history = conversation_store[session_id]

    print(f"[app] Processing message: {message[:80]}...")
    result = agent.process_query(message, history)

    # Keep only the latest memory block
    history = [item for item in history if item.get("role") != "system_memory"]

    if result.get("memory"):
        history.append({"role": "system_memory", "memory": result["memory"]})

    history.append({"role": "user", "text": message})
    history.append({"role": "bot", "text": result["text"]})

    conversation_store[session_id] = _trim_history(history)

    return jsonify({
        "text": result["text"],
        "intent": result.get("intent", "general"),
        "district": result.get("district"),
        "memory": result.get("memory", {}),
        "session_id": session_id,
    })


@app.route("/soil", methods=["POST"])
def soil():
    """
    Soil image classification endpoint.
    """
    print("[app] Received /soil request")

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_image_file(file.filename):
        return jsonify({"error": "Unsupported image format. Use JPG, JPEG, PNG, or WEBP."}), 400

    session_id = (request.form.get("session_id") or "").strip() or str(uuid.uuid4())

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    history = conversation_store[session_id]

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_DIR / unique_name
    file.save(filepath)

    try:
        classify = _get_soil_classifier()
        if classify is None:
            return jsonify({
                "error": "Soil classifier model not available. Make sure soil_classifier.py and soil_classification_model.h5 exist."
            }), 503

        print("[app] Running soil classification...")
        soil_type = classify(str(filepath))
        print(f"[app] Soil detected: {soil_type}")

        district_input = (request.form.get("district") or "").strip()
        district = de.fuzzy_district(district_input) if district_input else None
        suggestion_text = ""

        if district:
            raw = de.get_top_crops(district, soil_type.lower(), top_n=5)
            if "crops" in raw and raw["crops"]:
                crops_list = ", ".join([c["crop_name"] for c in raw["crops"][:5]])
                suggestion_text = f"\n\n🌾 **Best matching crops for {soil_type} in {district}:** {crops_list}"

        latest_memory = {
            "district": district or None,
            "soil": soil_type.lower(),
            "season": None,
            "crop": None,
        }

        # Preserve previous remembered fields where possible
        for item in history:
            if item.get("role") == "system_memory" and isinstance(item.get("memory"), dict):
                old = item["memory"]
                latest_memory["district"] = latest_memory["district"] or old.get("district")
                latest_memory["season"] = old.get("season")
                latest_memory["crop"] = old.get("crop")

        history = [item for item in history if item.get("role") != "system_memory"]
        history.append({"role": "system_memory", "memory": latest_memory})

        soil_profile = nlg.SOIL_PROFILES.get(soil_type, {})
        soil_character = soil_profile.get("character", "Typical characteristics for this soil type")

        text = (
            f"### 🏔️ Soil Analysis Result\n\n"
            f"**Detected Soil Type: {soil_type}**\n\n"
            f"| Soil Type | Characteristics |\n"
            f"|-----------|----------------|\n"
            f"| **{soil_type}** | {soil_character} |"
            f"{suggestion_text}\n\n"
            f"✅ I’ll remember this soil type for the rest of this chat."
        )

        history.append({"role": "user", "text": "[Uploaded soil image]"})
        history.append({"role": "bot", "text": text})
        conversation_store[session_id] = _trim_history(history)

        return jsonify({
            "soil_type": soil_type,
            "text": text,
            "session_id": session_id,
            "memory": latest_memory
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500

    finally:
        if filepath.exists():
            filepath.unlink()


@app.route("/districts", methods=["GET"])
def districts():
    return jsonify(de.get_all_districts())


@app.route("/reset_session", methods=["POST"])
def reset_session():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    if session_id and session_id in conversation_store:
        del conversation_store[session_id]
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
