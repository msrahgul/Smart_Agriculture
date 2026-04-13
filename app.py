"""
app.py – Smart Farming AI Agent: Flask Server
"""
from flask import Flask, request, jsonify, render_template, session
import os
import uuid
import pandas as pd
from werkzeug.utils import secure_filename
import data_engine as de
import agent

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory conversation history: {session_id: [{"role": "user"|"bot", "text": str}]}
conversation_store: dict = {}

# ── Load all datasets at startup ────────────────────────────────────────────────
de.load_data()

# ── Lazy import soil classifier (heavy TF load) ─────────────────────────────────
_soil_classifier_loaded = False
_classify_soil = None

def _get_soil_classifier():
    global _soil_classifier_loaded, _classify_soil
    if not _soil_classifier_loaded:
        from soil_classifier import classify_soil
        _classify_soil = classify_soil
        _soil_classifier_loaded = True
    return _classify_soil


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', districts=de.ALL_DISTRICTS)


@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint. Accepts {message, session_id}"""
    data = request.get_json(force=True)
    message = (data.get('message') or '').strip()
    session_id = data.get('session_id') or str(uuid.uuid4())

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    history = conversation_store[session_id]

    # Process with agent
    result = agent.process_query(message, history)

    # Persist history (keep last 20 turns)
    history.append({"role": "user", "text": message})
    history.append({"role": "bot", "text": result["text"]})
    if len(history) > 40:
        conversation_store[session_id] = history[-40:]

    return jsonify({
        "text": result["text"],
        "intent": result.get("intent", "general"),
        "district": result.get("district"),
        "session_id": session_id,
    })


@app.route('/soil', methods=['POST'])
def soil():
    """Soil image classification endpoint."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(filepath)

    try:
        classify = _get_soil_classifier()
        soil_type = classify(filepath)

        # Give quick crop suggestion for identified soil
        district = request.form.get('district', '').strip()
        suggestion_text = ""
        if district:
            raw = de.get_top_crops(district, soil_type.lower(), top_n=5)
            if "crops" in raw:
                crops_list = ", ".join([c["crop_name"] for c in raw["crops"][:5]])
                suggestion_text = f"\n\n🌾 **Top crops for {soil_type} in {district}:** {crops_list}"

        text = (
            f"### 🏔️ Soil Analysis Result\n\n"
            f"**Detected Soil Type: {soil_type}**\n\n"
            f"| Soil Type | Characteristics |\n"
            f"|-----------|----------------|\n"
            f"| **{soil_type}** | {_soil_description(soil_type)} |"
            f"{suggestion_text}"
        )
        return jsonify({'soil_type': soil_type, 'text': text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


def _soil_description(soil_type: str) -> str:
    descriptions = {
        'Alluvial soil': 'Fertile, fine-grained; excellent for rice, sugarcane, wheat, jute',
        'Black soil': 'High clay content, moisture-retentive; ideal for cotton, jowar, groundnut',
        'Clay soil': 'Heavy and sticky; suitable for paddy, vegetables, legumes',
        'Red soil': 'Well-drained, iron-rich; good for groundnut, ragi, millets, pulses',
    }
    return descriptions.get(soil_type, 'A soil type found in Tamil Nadu')


@app.route('/districts', methods=['GET'])
def districts():
    return jsonify(de.get_all_districts())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
