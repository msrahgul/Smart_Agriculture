"""
train_pest_risk_model.py – Train Random Forest Pest Risk Classifier
Usage: python train_pest_risk_model.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

DATA_PATH = Path("data/TamilNadu_ML_Master_Historical.csv")
MODEL_PATH = Path("models/pest_risk_model.pkl")
ENCODER_PATH = Path("models/pest_label_encoder.pkl")
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

print("Loading dataset...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip().str.lower()
df = df.drop_duplicates()
print(f"  Loaded {len(df):,} rows")


def derive_pest_risk(row):
    """
    Rule-based pest risk label derived from agroclimate conditions.
    High = 6+ score, Medium = 3-5, Low = 0-2
    """
    score = 0
    total_rain = row.get("district_rain_total_mm", 0) or 0
    rainy_days  = row.get("district_rainy_days", 0) or 0
    ne_monsoon  = row.get("district_ne_monsoon_rain_mm", 0) or 0
    sw_monsoon  = row.get("district_sw_monsoon_rain_mm", 0) or 0
    crop        = str(row.get("crop_name", "")).lower()
    season      = str(row.get("season", "")).lower()

    if total_rain > 1000: score += 2
    elif total_rain > 700: score += 1

    if rainy_days > 70: score += 2
    elif rainy_days > 45: score += 1

    if ne_monsoon > 300: score += 1
    if sw_monsoon > 300: score += 1

    if crop in ["rice", "paddy", "banana", "sugarcane", "cotton", "maize"]:
        score += 1
    if season in ["kharif", "rabi"]:
        score += 1

    if score >= 6: return "High"
    elif score >= 3: return "Medium"
    return "Low"


print("Deriving pest risk labels...")
df["pest_risk"] = df.apply(derive_pest_risk, axis=1)
dist = df["pest_risk"].value_counts()
print(f"  Label distribution:\n{dist.to_string()}")

drop_cols = ["pest_risk", "yield", "production", "production_units", "area_units", "agri_year_label"]
drop_cols = [c for c in drop_cols if c in df.columns]

X = df.drop(columns=drop_cols)
y = df["pest_risk"]

categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
numeric_cols     = X.select_dtypes(include=[np.number]).columns.tolist()
print(f"\n  Features: {len(numeric_cols)} numeric, {len(categorical_cols)} categorical")

numeric_transformer = Pipeline([("imputer", SimpleImputer(strategy="median"))])
categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])
preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_cols),
    ("cat", categorical_transformer, categorical_cols),
])

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
print(f"  Classes: {list(label_encoder.classes_)}")

model = RandomForestClassifier(
    n_estimators=250, max_depth=14,
    min_samples_split=5, min_samples_leaf=2,
    random_state=42, n_jobs=-1,
)
pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])

X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)
print(f"\nTraining on {len(X_train):,} samples, testing on {len(X_test):,}...")

pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

print("\n" + "="*40)
print("  Pest Risk Model Performance")
print("="*40)
print(f"  Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print("\n  Classification Report:")
print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
print("="*40)

joblib.dump(pipeline, MODEL_PATH)
joblib.dump(label_encoder, ENCODER_PATH)
print(f"\n✅ Saved pest model    → {MODEL_PATH}")
print(f"✅ Saved label encoder → {ENCODER_PATH}")
