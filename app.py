
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

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
conversation_store: dict = {}

de.load_data()
ml_models.load_models()
_classify_soil = None


def allowed_image_file(filename: str) -> bool:
    return bool(filename and "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_IMAGE_EXTENSIONS)


def _load_soil_classifier():
    global _classify_soil
    try:
        from soil_classifier import classify_soil
        _classify_soil = classify_soil
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
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    history = conversation_store[session_id]
    result = agent.process_query(message, history)

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


@app.route("/set_context", methods=["POST"])
def set_context():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())
    memory = data.get("memory") or {}
    clean = {
        "district": memory.get("district") or None,
        "soil": memory.get("soil") or None,
        "season": memory.get("season") or None,
        "month": memory.get("month") or None,
        "crop": memory.get("crop") or None,
    }
    history = [item for item in conversation_store.get(session_id, []) if item.get("role") != "system_memory"]
    history.append({"role": "system_memory", "memory": clean})
    conversation_store[session_id] = _trim_history(history)
    return jsonify({"ok": True, "session_id": session_id, "memory": clean})


@app.route("/soil", methods=["POST"])
def soil():
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
            return jsonify({"error": "Soil classifier model not available."}), 503
        soil_type = classify(str(filepath))
        district_input = (request.form.get("district") or "").strip()
        district = de.fuzzy_district(district_input) if district_input else None
        suggestion_text = ""
        if district:
            raw = de.get_top_crops(district, soil_type.lower(), top_n=5)
            if "crops" in raw and raw["crops"]:
                crops_list = ", ".join([c["crop_name"] for c in raw["crops"][:5]])
                suggestion_text = f"\n\n**Best matching crops for {soil_type} in {district}:** {crops_list}"

        latest_memory = {"district": district or None, "soil": soil_type.lower(), "season": None, "month": None, "crop": None}
        for item in history:
            if item.get("role") == "system_memory" and isinstance(item.get("memory"), dict):
                old = item["memory"]
                for key in latest_memory:
                    latest_memory[key] = latest_memory[key] or old.get(key)

        history = [item for item in history if item.get("role") != "system_memory"]
        history.append({"role": "system_memory", "memory": latest_memory})

        soil_profile = nlg.SOIL_PROFILES.get(soil_type, {})
        soil_character = soil_profile.get("character", "Typical characteristics for this soil type")
        text = (
            f"### Soil Analysis Result\n\n"
            f"**Detected soil type:** {soil_type}\n\n"
            f"**Characteristics:** {soil_character}."
            f"{suggestion_text}\n\n"
            f"I'll remember this soil type for the rest of this chat."
        )
        history.append({"role": "user", "text": "[Uploaded soil image]"})
        history.append({"role": "bot", "text": text})
        conversation_store[session_id] = _trim_history(history)
        return jsonify({"soil_type": soil_type, "text": text, "session_id": session_id, "memory": latest_memory})
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
