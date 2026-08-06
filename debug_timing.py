"""Full end-to-end timing test — simulates the Flask context."""
import time
import data_engine as de
import ml_models

# Mimic app.py startup
de.load_data()
ml_models.load_models()

from agent import process_query

queries = [
    "What crops grow in Madurai?",
    "How much rainfall does Coimbatore get?",
    "Pest risk for rice in Thanjavur?",
    "Overview of Erode district?",
    "Fertilizer recommendation for sugarcane?",
]

for q in queries:
    t0 = time.time()
    result = process_query(q)
    elapsed = time.time() - t0
    preview = result.get("text", "")[:150].replace("\n", " ")
    print(f"[{elapsed:.1f}s] Q: {q}")
    print(f"       A: {preview}...")
    print()
