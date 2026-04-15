"""
train_yield_model.py – Train Random Forest Yield Predictor
Usage: python train_yield_model.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DATA_PATH = Path("data/TamilNadu_ML_Master_Historical.csv")
MODEL_PATH = Path("models/yield_model.pkl")
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

print("Loading dataset...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip().str.lower()
df = df.drop_duplicates()
print(f"  Loaded {len(df):,} rows")

TARGET = "yield"
if TARGET not in df.columns:
    raise ValueError(f"'{TARGET}' column not found in dataset. Available: {list(df.columns)}")

df = df.dropna(subset=[TARGET])
df = df[df[TARGET] > 0]
print(f"  After filtering nulls/zeros: {len(df):,} rows")

# Remove extreme outliers via IQR
q1 = df[TARGET].quantile(0.25)
q3 = df[TARGET].quantile(0.75)
iqr = q3 - q1
lower = max(0, q1 - 1.5 * iqr)
upper = q3 + 1.5 * iqr
df = df[(df[TARGET] >= lower) & (df[TARGET] <= upper)]
print(f"  After outlier removal: {len(df):,} rows | yield range: [{lower:.2f}, {upper:.2f}] t/ha")

drop_cols = ["yield", "production", "production_units", "area_units", "agri_year_label"]
drop_cols = [c for c in drop_cols if c in df.columns]

X = df.drop(columns=drop_cols)
y = df[TARGET]

categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
print(f"  Features: {len(numeric_cols)} numeric, {len(categorical_cols)} categorical")

numeric_transformer = Pipeline([("imputer", SimpleImputer(strategy="median"))])
categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])
preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_cols),
    ("cat", categorical_transformer, categorical_cols),
])

model = RandomForestRegressor(
    n_estimators=300, max_depth=18,
    min_samples_split=5, min_samples_leaf=2,
    random_state=42, n_jobs=-1,
)
pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"\nTraining on {len(X_train):,} samples, testing on {len(X_test):,}...")

pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)

print("\n" + "="*40)
print("  Yield Model Performance")
print("="*40)
print(f"  MAE  : {mae:.4f} t/ha")
print(f"  RMSE : {rmse:.4f} t/ha")
print(f"  R²   : {r2:.4f}")
print("="*40)

joblib.dump(pipeline, MODEL_PATH)
print(f"\n✅ Saved yield model → {MODEL_PATH}")
