"""Train an interpretable, match-grouped logistic-regression baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    log_loss,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "outcome_label"
NUMERIC_FEATURES = [
    "minute",
    "team_score_at_substitution",
    "opponent_score_at_substitution",
    "score_difference_at_substitution",
]
CATEGORICAL_FEATURES = ["team_side", "score_state"]
CLASSES = ["negative", "neutral", "positive"]


def prepare_model_table(path: str | Path) -> pd.DataFrame:
    """Load the match-state table and retain only pre-outcome information."""
    frame = pd.read_csv(path)
    required = {
        "match_id", TARGET, "minute", "team_score_at_substitution",
        "opponent_score_at_substitution", "team_side", "score_state",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    frame = frame.dropna(subset=list(required)).copy()
    frame["score_difference_at_substitution"] = (
        frame["team_score_at_substitution"] - frame["opponent_score_at_substitution"]
    )
    frame = frame[frame[TARGET].isin(CLASSES)]
    return frame


def train_baseline(
    data_path: str | Path,
    model_path: str | Path,
    metrics_path: str | Path,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Split by match, train logistic regression, and save model and metrics."""
    frame = prepare_model_table(data_path)
    if frame["match_id"].nunique() < 5:
        raise ValueError("At least five distinct matches are required for a grouped split.")

    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = frame[features]
    y = frame[TARGET].astype(str)
    groups = frame["match_id"]

    splitter = GroupShuffleSplit(
        n_splits=1, test_size=test_size, random_state=random_state
    )
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=random_state
        )),
    ])
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)
    model_classes = pipeline.named_steps["classifier"].classes_
    metrics = {
        "model": "logistic_regression_baseline",
        "target": TARGET,
        "features": features,
        "split": "GroupShuffleSplit by match_id",
        "random_state": random_state,
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_matches": int(groups.iloc[train_idx].nunique()),
        "test_matches": int(groups.iloc[test_idx].nunique()),
        "classes": [str(value) for value in model_classes],
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, average="macro")),
        "log_loss": float(log_loss(y_test, probabilities, labels=model_classes)),
        "confusion_matrix_labels": [str(value) for value in model_classes],
        "confusion_matrix": confusion_matrix(
            y_test, predictions, labels=model_classes
        ).tolist(),
        "classification_report": classification_report(
            y_test, predictions, labels=model_classes, output_dict=True, zero_division=0
        ),
        "test_class_distribution": {
            str(key): int(value) for key, value in y_test.value_counts().items()
        },
    }

    model_file = Path(model_path)
    metrics_file = Path(metrics_path)
    model_file.parent.mkdir(parents=True, exist_ok=True)
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_file)
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/processed/substitution_match_state.csv")
    parser.add_argument("--model", default="models/logistic_regression_baseline.joblib")
    parser.add_argument("--metrics", default="reports/baseline_metrics.json")
    args = parser.parse_args()

    metrics = train_baseline(args.data, args.model, args.metrics)
    print("Baseline model:", metrics["model"])
    print("Rows:", metrics["train_rows"] + metrics["test_rows"])
    print("Train/test matches:", metrics["train_matches"], "/", metrics["test_matches"])
    print("Accuracy:", round(metrics["accuracy"], 4))
    print("Balanced accuracy:", round(metrics["balanced_accuracy"], 4))
    print("Macro F1:", round(metrics["macro_f1"], 4))
    print("Log loss:", round(metrics["log_loss"], 4))
    print("Saved model:", args.model)
    print("Saved metrics:", args.metrics)


if __name__ == "__main__":
    main()
