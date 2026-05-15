#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List, Tuple

import numpy as np

FEATURE_NAMES = [
    'torso_distance_norm',
    'wrap_score',
    'lift_score',
    'feet_off_ground_score',
    'limb_speed_score',
    'limb_accel_score',
    'co_motion_score',
]


def package_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def seed_dataset() -> Tuple[np.ndarray, np.ndarray]:
    # Seed data is for engineering/demo only. Replace or extend with real labeled staged data.
    rows = []
    labels = []

    def add(label, vals, repeat=1):
        for _ in range(repeat):
            rows.append(vals)
            labels.append(label)

    # normal: far apart / low motion
    add('normal', [4.5, 0.0, 0.0, 0.0, 0.05, 0.05, 0.0], 20)
    add('normal', [3.0, 0.0, 0.0, 0.0, 0.10, 0.10, 0.05], 20)
    add('normal', [2.0, 0.05, 0.0, 0.0, 0.20, 0.20, 0.05], 20)

    # warning: close contact / moderate movement
    add('warning', [1.0, 0.5, 0.15, 0.10, 0.45, 0.45, 0.25], 20)
    add('warning', [0.8, 0.55, 0.25, 0.15, 0.55, 0.50, 0.35], 20)
    add('warning', [1.1, 0.45, 0.30, 0.15, 0.65, 0.55, 0.40], 20)

    # high: close + lift/feet/limb/comotion evidence
    add('high', [0.4, 0.90, 0.80, 0.70, 0.90, 0.85, 0.75], 25)
    add('high', [0.3, 1.00, 0.95, 0.90, 1.00, 0.95, 0.85], 25)
    add('high', [0.6, 0.85, 0.75, 0.65, 0.95, 0.90, 0.80], 25)

    rng = np.random.default_rng(42)
    X = np.asarray(rows, dtype=float)
    X += rng.normal(0.0, 0.035, X.shape)
    X[:, 0] = np.clip(X[:, 0], 0.0, 5.0)
    X[:, 1:] = np.clip(X[:, 1:], 0.0, 1.0)
    y = np.asarray(labels)
    return X, y


def load_csv_data(data_dir: Path) -> Tuple[List[List[float]], List[str]]:
    X, y = [], []
    for path in sorted(data_dir.glob('*.csv')):
        with path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    X.append([float(row[name]) for name in FEATURE_NAMES])
                    y.append(str(row['label']).strip().lower())
                except Exception:
                    continue
    return X, y


def main() -> None:
    parser = argparse.ArgumentParser(description='Train feature-based AI risk model.')
    parser.add_argument('--data-dir', default='data/feature_logs')
    parser.add_argument('--output', default=str(package_dir() / 'models' / 'risk_model.joblib'))
    parser.add_argument('--use-seed', action='store_true', help='Use built-in seed dataset if data is missing or too small.')
    args = parser.parse_args()

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    import joblib

    X_list, y_list = load_csv_data(Path(args.data_dir))
    use_seed = args.use_seed or len(set(y_list)) < 2 or len(X_list) < 30
    if use_seed:
        print('Using built-in seed dataset. Replace/extend this with real staged labeled data later.')
        X, y = seed_dataset()
    else:
        X = np.asarray(X_list, dtype=float)
        y = np.asarray(y_list)

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        class_weight='balanced',
    )

    if len(set(y)) >= 2 and len(y) >= 12:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        clf.fit(X_train, y_train)
        print(classification_report(y_test, clf.predict(X_test)))
    else:
        clf.fit(X, y)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'model': clf,
        'feature_names': FEATURE_NAMES,
        'model_version': 'feature-rf-v1',
        'classes': [str(c) for c in clf.classes_],
    }
    joblib.dump(payload, output)
    meta = {
        'model_version': 'feature-rf-v1',
        'feature_names': FEATURE_NAMES,
        'classes': [str(c) for c in clf.classes_],
        'trained_with_seed_data': bool(use_seed),
        'note': 'Seed data is for demo only. Replace with real safe staged labeled feature logs.',
    }
    output.with_suffix('.json').write_text(json.dumps(meta, indent=2))
    print(f'Saved model: {output}')
    print(f'Saved metadata: {output.with_suffix(".json")}')


if __name__ == '__main__':
    main()
