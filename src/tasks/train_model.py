#!/usr/bin/env python3
"""
Simple training script (example).
Trains a very small synthetic model and saves it to models/props_model.pkl
This is a placeholder; replace with real training logic when you have labeled data.
"""
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

os.makedirs("models", exist_ok=True)
MODEL_PATH = "models/props_model.pkl"
SCALER_PATH = "models/scaler.pkl"

def train_synthetic_model():
    # synthetic dataset: features -> binary over/under label
    rng = np.random.RandomState(42)
    X = rng.randn(500, 8)
    # make label correlated with first column
    y = (X[:, 0] + 0.5 * rng.randn(500) > 0).astype(int)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(Xs, y)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"Trained synthetic model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_synthetic_model()
