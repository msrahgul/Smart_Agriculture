# Smart Agriculture Application

This project is a **Smart Agriculture Web Application** that provides intelligent insights for farmers, including crop recommendations based on soil type, district characteristics, rainfall patterns, wage metrics, and fertilizer consumption guidelines. It utilizes a Flask backend, machine learning models for image-based soil classification, and predictive models for crop yield and pest risk assessment.

## Features

- **Web UI & Interactive Chat:** A streamlined Flask-based web interface to upload soil images and chat intelligently about district-level farming data.
- **Soil Classification:** Detects soil type from uploaded images using a pre-trained Deep Learning model.
- **Crop Recommendations & Yield Prediction:** Recommends the best crops for a specific district and soil type, while forecasting expected yield.
- **Pest Risk Assessment:** Predicts the risk of local pests based on crop type and conditions.
- **Comprehensive Agricultural Data:** Retrieves and synthesizes data on monthly rainfall, daily wages, and expected fertilizer consumption (Kharif/Rabi seasons).

## Project Structure

```bash
.
├── app.py                     # Main Flask application
├── agent.py                   # Agricultural AI agent logic
├── data_engine.py             # Tools for retrieving district and crop data
├── soil_classifier.py         # Image-based soil classification logic
├── recommendation.py          # Support recommendation logic
├── nlg.py                     # Natural Language Generation helper
├── models/                    # Saved ML models (.h5 for soil, .pkl for crops/pests)
├── data/                      # CSV datasets for districts, crops, and historical data
├── static/                    # CSS, JS, and asset files
├── templates/                 # HTML templates
└── requirements.txt           # Python dependencies
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Create a virtual environment (recommended):
  ```bash
  python -m venv .venv
  .venv\Scripts\activate
  ```

### Installation

Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root directory. Configure necessary keys if your agent relies on external APIs (e.g., Gemini API key) or custom configurations.

### Running the Application

Start the Flask server:
```bash
python app.py
```

The application will be accessible at `http://127.0.0.1:5000/`.

1. Access the web interface in your browser.
2. Upload an image of the soil if prompted.
3. Enter your district and any queries you have in the chat window.
4. The AI agent will extract relevant contextual data, classify the soil, predict the best crop yields, and provide actionable insights.

## Notes

- Ensure that the image file selected for soil classification is clear and well-lit for better accuracy.
- Currently supports districts within Tamil Nadu.

## Future Improvements

- Incorporate real-time weather forecasting API integrations.
- Further enhance the LLM-based parsing and contextual data retrieval.
- Expand support for regional languages to improve accessibility for farmers.

## License

This project is open-source and available under the MIT License.
