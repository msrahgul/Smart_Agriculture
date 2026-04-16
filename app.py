
"""
app.py – Smart Farming AI Agent: Flask Server
"""

from flask import Flask, request, jsonify, render_template
import os
import uuid
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
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

DISTRICT_COORDS = {
    "Ariyalur": (11.14, 79.08),
    "Chengalpattu": (12.69, 79.98),
    "Chennai": (13.08, 80.27),
    "Coimbatore": (11.02, 76.96),
    "Cuddalore": (11.75, 79.77),
    "Dharmapuri": (12.13, 78.16),
    "Dindigul": (10.36, 77.97),
    "Erode": (11.34, 77.72),
    "Kallakurichi": (11.74, 78.96),
    "Kancheepuram": (12.83, 79.70),
    "Kanniyakumari": (8.08, 77.55),
    "Karur": (10.96, 78.08),
    "Krishnagiri": (12.52, 78.21),
    "Madurai": (9.93, 78.12),
    "Mayiladuthurai": (11.10, 79.65),
    "Nagapattinam": (10.77, 79.84),
    "Namakkal": (11.22, 78.17),
    "Perambalur": (11.23, 78.88),
    "Pudukkottai": (10.38, 78.82),
    "Ramanathapuram": (9.37, 78.83),
    "Ranipet": (12.93, 79.33),
    "Salem": (11.66, 78.15),
    "Sivagangai": (9.85, 78.48),
    "Tenkasi": (8.96, 77.32),
    "Thanjavur": (10.79, 79.14),
    "The Nilgiris": (11.41, 76.70),
    "Theni": (10.01, 77.48),
    "Thoothukudi": (8.76, 78.13),
    "Tiruchirapalli": (10.79, 78.70),
    "Tirunelveli": (8.71, 77.76),
    "Tirupathur": (12.50, 78.57),
    "Tiruppur": (11.11, 77.34),
    "Tiruvallur": (13.14, 79.91),
    "Tiruvannamalai": (12.23, 79.07),
    "Tiruvarur": (10.77, 79.63),
    "Vellore": (12.92, 79.13),
    "Villupuram": (11.94, 79.49),
    "Virudhunagar": (9.59, 77.95),
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Slight showers",
    81: "Moderate showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}

DISTRICT_TEMP_BASE = {
    "Chennai": 31,
    "Coimbatore": 29,
    "Kanniyakumari": 29,
    "Madurai": 31,
    "Ramanathapuram": 32,
    "The Nilgiris": 18,
    "Thoothukudi": 31,
}

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


def _weather_summary_text(code):
    try:
        return WEATHER_CODES.get(int(code), "Weather update")
    except (TypeError, ValueError):
        return "Weather update"


def _series_value(series: dict, key: str, index: int):
    values = series.get(key) or []
    return values[index] if index < len(values) else None


def _local_weather_fallback(district: str, reason: str = "offline") -> dict:
    district_name = de.fuzzy_district(district)
    if not district_name:
        return {"error": "District not found."}

    rain_stats = de.get_rainfall_stats(district_name)
    annual_rain = float(rain_stats.get("avg_annual_mm", 850) or 850) if "error" not in rain_stats else 850.0
    today = date.today()
    month = today.month
    rainy_month = month in {6, 7, 8, 9, 10, 11, 12}
    base_temp = DISTRICT_TEMP_BASE.get(district_name, 30)
    seasonal_adjust = -2 if month in {11, 12, 1, 2} else (2 if month in {4, 5, 6} else 0)
    rain_probability = max(10, min(85, round((annual_rain / 1400) * (58 if rainy_month else 30))))
    current_rain = round((annual_rain / 365) * (1.8 if rainy_month else 0.55), 1)
    condition = "Offline seasonal rain estimate" if rain_probability >= 45 else "Offline seasonal weather estimate"

    hourly = []
    for idx in range(4):
        hour = idx * 3
        timestamp = f"{today.isoformat()}T{(8 + hour) % 24:02d}:00"
        hourly.append({
            "time": timestamp,
            "temp_c": round(base_temp + seasonal_adjust + (idx * 0.8), 1),
            "humidity_pct": max(45, min(92, round(62 + (annual_rain / 1000 * 10) + (8 if rainy_month else 0)))),
            "rain_probability_pct": max(5, min(95, rain_probability - idx * 3)),
            "rain_mm": round(current_rain / 4, 1),
            "condition": condition,
        })

    daily = []
    for idx in range(3):
        day = today + timedelta(days=idx)
        daily.append({
            "date": day.isoformat(),
            "condition": condition,
            "temp_max_c": round(base_temp + seasonal_adjust + 3 + idx * 0.4, 1),
            "temp_min_c": round(base_temp + seasonal_adjust - 5, 1),
            "rain_sum_mm": round(current_rain * (1 + idx * 0.15), 1),
            "rain_probability_pct": max(5, min(95, rain_probability + idx * 4)),
        })

    return {
        "district": district_name,
        "source": "Offline estimate",
        "fallback": True,
        "fallback_reason": reason,
        "current": {
            "time": today.isoformat(),
            "temp_c": round(base_temp + seasonal_adjust, 1),
            "humidity_pct": hourly[0]["humidity_pct"],
            "precipitation_mm": current_rain,
            "rain_mm": current_rain,
            "wind_kmh": 10,
            "condition": condition,
        },
        "hourly": hourly,
        "daily": daily,
    }


def _open_meteo_weather(district: str) -> dict:
    district_name = de.fuzzy_district(district)
    if not district_name:
        return {"error": "District not found."}
    coords = DISTRICT_COORDS.get(district_name)
    if not coords:
        return {"error": f"Weather coordinates unavailable for {district_name}."}

    lat, lon = coords
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 3,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    with urlopen(url, timeout=8) as response:
        import json
        raw = json.loads(response.read().decode("utf-8"))

    current = raw.get("current") or {}
    hourly = raw.get("hourly") or {}
    daily = raw.get("daily") or {}

    hourly_rows = []
    for idx, time_value in enumerate((hourly.get("time") or [])[:8]):
        hourly_rows.append({
            "time": time_value,
            "temp_c": _series_value(hourly, "temperature_2m", idx),
            "humidity_pct": _series_value(hourly, "relative_humidity_2m", idx),
            "rain_probability_pct": _series_value(hourly, "precipitation_probability", idx),
            "rain_mm": _series_value(hourly, "precipitation", idx),
            "condition": _weather_summary_text(_series_value(hourly, "weather_code", idx)),
        })

    daily_rows = []
    for idx, time_value in enumerate((daily.get("time") or [])[:3]):
        daily_rows.append({
            "date": time_value,
            "condition": _weather_summary_text(_series_value(daily, "weather_code", idx)),
            "temp_max_c": _series_value(daily, "temperature_2m_max", idx),
            "temp_min_c": _series_value(daily, "temperature_2m_min", idx),
            "rain_sum_mm": _series_value(daily, "precipitation_sum", idx),
            "rain_probability_pct": _series_value(daily, "precipitation_probability_max", idx),
        })

    return {
        "district": district_name,
        "source": "Open-Meteo",
        "latitude": lat,
        "longitude": lon,
        "current": {
            "time": current.get("time"),
            "temp_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "rain_mm": current.get("rain"),
            "wind_kmh": current.get("wind_speed_10m"),
            "condition": _weather_summary_text(current.get("weather_code")),
        },
        "hourly": hourly_rows,
        "daily": daily_rows,
    }


@app.route("/weather", methods=["GET"])
def weather():
    district = (request.args.get("district") or "").strip()
    if not district:
        return jsonify({"error": "District is required."}), 400
    try:
        data = _open_meteo_weather(district)
        status = 404 if "error" in data else 200
        return jsonify(data), status
    except Exception as e:
        data = _local_weather_fallback(district, type(e).__name__)
        status = 404 if "error" in data else 200
        return jsonify(data), status


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.route("/simulate_advanced", methods=["POST"])
def simulate_advanced():
    data = request.get_json(silent=True) or {}
    language = (data.get("language") or "en").strip().lower()
    district = de.fuzzy_district(data.get("district") or "")
    crop = str(data.get("crop") or "selected crop").strip() or "selected crop"
    if not district:
        return jsonify({"error": "Set a district first to run the simulator."}), 400

    rainfall = _num(data.get("rainfall_delta_mm"))
    irrigation = _num(data.get("irrigation_delta_pct"))
    fertilizer = _num(data.get("fertilizer_delta_pct"))
    temperature = _num(data.get("temperature_delta_c"))
    pest = _num(data.get("pest_intensity_pct"))
    moisture = _num(data.get("soil_moisture_pct"))

    base_score = None
    modified_score = None
    if crop and crop.lower() != "selected crop":
        baseline = de.compute_suitability_score(district, crop, data.get("soil"), data.get("season"))
        modified = de.compute_suitability_score(
            district,
            crop,
            data.get("soil"),
            data.get("season"),
            irrigation_delta_pct=irrigation,
            extra_rainfall_mm=rainfall,
        )
        if "error" not in baseline:
            base_score = baseline.get("score")
        if "error" not in modified:
            modified_score = modified.get("score")

    score_delta = ((modified_score or 5.0) - (base_score or 5.0)) * 4
    fertilizer_effect = max(-8, min(10, fertilizer * 0.12))
    temp_effect = -abs(temperature) * 2.2 if abs(temperature) > 1 else temperature * 0.8
    moisture_effect = -abs(moisture - 55) * 0.16 + 6
    pest_effect = -pest * 0.22
    yield_impact = round(max(-45, min(35, score_delta + fertilizer_effect + temp_effect + moisture_effect + pest_effect)), 1)
    pest_risk_change = round(max(-25, min(55, pest * 0.55 + max(0, moisture - 70) * 0.45 + max(0, rainfall) * 0.015 - max(0, fertilizer) * 0.04)), 1)

    if pest_risk_change > 20:
        action = "High pest pressure: inspect leaves twice weekly and avoid unnecessary irrigation."
    elif yield_impact < -10:
        action = "Yield may drop: rebalance water, reduce stress, and consider staged fertilizer support."
    elif yield_impact > 8:
        action = "Scenario looks favorable: keep monitoring moisture and avoid over-fertilizing."
    else:
        action = "Scenario is stable: maintain current plan and monitor rainfall/pest signs."

    yield_direction = "increase" if yield_impact > 0 else ("decrease" if yield_impact < 0 else "stay nearly stable")
    pest_direction = "increase" if pest_risk_change > 0 else ("decrease" if pest_risk_change < 0 else "stay nearly stable")
    text = f"""## What-If Simulation: {crop.title()} in {district}

### Scenario Inputs
- Rainfall change: **{rainfall:g} mm**
- Irrigation change: **{irrigation:g}%**
- Fertilizer change: **{fertilizer:g}%**
- Temperature change: **{temperature:g} C**
- Pest intensity: **{pest:g}%**
- Soil moisture: **{moisture:g}%**

### Expected Result
- Expected yield impact: **{yield_impact}%**. Yield may **{yield_direction}** under this scenario.
- Pest risk change: **{pest_risk_change}%**. Pest pressure may **{pest_direction}**.

### Why This Happens
- Water availability is shaped by rainfall and irrigation together.
- Fertilizer helps only when moisture and pest pressure are manageable.
- Temperature stress and high pest intensity reduce the likely yield benefit.
- Soil moisture around the middle range is usually safer than very dry or waterlogged conditions.

### Recommended Action
{action}"""

    if language.startswith("ta"):
        text = agent._translate_same_template_to_tamil(text)

    return jsonify({
        "district": district,
        "crop": crop.title(),
        "base_score": base_score,
        "modified_score": modified_score,
        "yield_impact_pct": yield_impact,
        "pest_risk_change_pct": pest_risk_change,
        "recommended_action": action,
        "text": text,
    })


@app.route("/profit_estimate", methods=["POST"])
def profit_estimate():
    data = request.get_json(silent=True) or {}
    crop = str(data.get("crop") or "Crop").strip().title()
    acres = max(0.01, _num(data.get("acres"), 1.0))
    expected_yield = max(0, _num(data.get("expected_yield"), 0.0))
    fertilizer_cost = max(0, _num(data.get("fertilizer_cost"), 0.0))
    labor_cost = max(0, _num(data.get("labor_cost"), 0.0))
    irrigation_cost = max(0, _num(data.get("irrigation_cost"), 0.0))
    market_price = max(0, _num(data.get("market_price"), 0.0))

    revenue = expected_yield * acres * market_price
    total_cost = (fertilizer_cost + labor_cost + irrigation_cost) * acres
    profit = revenue - total_cost
    margin = (profit / revenue * 100) if revenue else 0

    if margin >= 25:
        risk = "Low"
        suggestion = "Profit margin is healthy. Lock input costs and watch market price before selling."
    elif margin >= 8:
        risk = "Medium"
        suggestion = "Profit is possible, but reduce avoidable input costs and compare local market prices."
    else:
        risk = "High"
        suggestion = "Profit is tight. Improve expected yield, reduce costs, or wait for better market price."

    return jsonify({
        "crop": crop,
        "acres": acres,
        "estimated_revenue": round(revenue),
        "total_cost": round(total_cost),
        "profit": round(profit),
        "profit_margin_pct": round(margin, 1),
        "risk_level": risk,
        "suggestion": suggestion,
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())
    language = (data.get("language") or "en").strip().lower()

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    history = conversation_store[session_id]
    result = agent.process_query(message, history, language=language)

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


@app.route("/session", methods=["GET"])
def get_session():
    session_id = (request.args.get("session_id") or "").strip()
    memory = {"district": None, "soil": None, "season": None, "month": None, "crop": None}
    messages = []
    if session_id and session_id in conversation_store:
        for item in conversation_store.get(session_id, []):
            if item.get("role") == "system_memory" and isinstance(item.get("memory"), dict):
                memory.update({key: item["memory"].get(key) or None for key in memory})
            elif item.get("role") in {"user", "bot"} and item.get("text"):
                messages.append({"role": item["role"], "text": item["text"]})
    return jsonify({"ok": True, "session_id": session_id or None, "memory": memory, "messages": messages})


@app.route("/soil", methods=["POST"])
def soil():
    language = (request.form.get("language") or "en").strip().lower()
    if "image" not in request.files:
        return jsonify({"error": "படம் வழங்கப்படவில்லை" if language.startswith("ta") else "No image provided"}), 400
    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "கோப்பு தேர்வு செய்யப்படவில்லை" if language.startswith("ta") else "No file selected"}), 400
    if not allowed_image_file(file.filename):
        return jsonify({"error": "ஆதரிக்கப்படாத படம் வடிவம். JPG, JPEG, PNG அல்லது WEBP பயன்படுத்தவும்." if language.startswith("ta") else "Unsupported image format. Use JPG, JPEG, PNG, or WEBP."}), 400

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
            return jsonify({"error": "மண் வகைப்படுத்தும் மாதிரி கிடைக்கவில்லை." if language.startswith("ta") else "Soil classifier model not available."}), 503
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
        if language.startswith("ta"):
            text = agent._translate_same_template_to_tamil(text)
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
