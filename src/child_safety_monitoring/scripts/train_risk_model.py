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

LABEL_MAP = {
    # normal / negative examples
    'normal': 'normal',
    'normal_far': 'normal',
    'normal_close': 'normal',
    'normal_hug': 'normal',
    'normal_play': 'normal',
    'normal_walk': 'normal',
    'standing': 'normal',
    'walking': 'normal',
    'hug': 'normal',

    # early suspicious / warning examples
    'warning': 'warning',
    'near': 'warning',
    'near_suspicious': 'warning',
    'suspicious_contact': 'warning',
    'approach_fast': 'warning',
    'arms_near': 'warning',

    # high risk examples
    'high': 'high',
    'high_suspicious': 'high',
    'critical': 'high',
    'critical_risk': 'high',
    'critical_like': 'high',
    'lift_like': 'high',
    'struggle_like': 'high',
}


def package_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def canonical_label(label: str) -> str:
    key = str(label).strip().lower().replace('-', '_').replace(' ', '_')
    if key not in LABEL_MAP:
        raise ValueError(f'Unknown label: {label}. Add it to LABEL_MAP or use known labels.')
    return LABEL_MAP[key]


def sanitize_feature(name: str, value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    value = float(value)
    if name == 'torso_distance_norm':
        return float(np.clip(value, 0.0, 5.0))
    return float(np.clip(value, 0.0, 1.0))


def seed_dataset() -> Tuple[np.ndarray, np.ndarray]:
    # Seed data is only for pipeline testing. Real robot-camera logs are required for meaningful performance.
    rows: List[List[float]] = []
    labels: List[str] = []

    def add(label: str, vals: List[float], repeat: int = 1) -> None:
        for _ in range(repeat):
            rows.append(vals)
            labels.append(label)

    # normal examples: far, close, calm hug/play
    add('normal', [4.5, 0.0, 0.0, 0.0, 0.05, 0.05, 0.0], 30)
    add('normal', [3.0, 0.0, 0.0, 0.0, 0.10, 0.10, 0.05], 30)
    add('normal', [1.6, 0.35, 0.0, 0.0, 0.10, 0.10, 0.05], 30)
    add('normal', [0.9, 0.55, 0.0, 0.0, 0.12, 0.12, 0.05], 30)

    # warning examples: close approach + arm posture but weak lift/struggle
    add('warning', [1.0, 0.65, 0.05, 0.0, 0.35, 0.30, 0.20], 25)
    add('warning', [0.8, 0.75, 0.10, 0.05, 0.45, 0.40, 0.30], 25)
    add('warning', [0.6, 0.85, 0.15, 0.05, 0.55, 0.45, 0.35], 25)

    # high examples: close + lift-like + rapid limb/co-motion evidence
    add('high', [0.4, 0.90, 0.65, 0.45, 0.75, 0.70, 0.55], 25)
    add('high', [0.3, 1.00, 0.80, 0.60, 0.90, 0.85, 0.70], 25)
    add('high', [0.6, 0.85, 0.70, 0.50, 0.85, 0.80, 0.65], 25)

    rng = np.random.default_rng(42)
    X = np.asarray(rows, dtype=float)
    X += rng.normal(0.0, 0.035, X.shape)
    X[:, 0] = np.clip(X[:, 0], 0.0, 5.0)
    X[:, 1:] = np.clip(X[:, 1:], 0.0, 1.0)
    y = np.asarray(labels)
    return X, y


def load_csv_data(data_dir: Path) -> Tuple[List[List[float]], List[str]]:
    X: List[List[float]] = []
    y: List[str] = []
    for path in sorted(data_dir.glob('*.csv')):
        with path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    label = canonical_label(row['label'])
                    features = [sanitize_feature(name, float(row[name])) for name in FEATURE_NAMES]
                    X.append(features)
                    y.append(label)
                except Exception as exc:
                    print(f'Skipped row in {path.name}: {exc}')
                    continue
    return X, y


def print_dataset_summary(y: np.ndarray) -> None:
    print('Dataset summary:')
    for label in sorted(set(y)):
        print(f'  {label}: {(y == label).sum()} samples')


def main() -> None:
    parser = argparse.ArgumentParser(description='Train feature-based AI risk model from robot-camera feature logs.')
    parser.add_argument('--data-dir', default='data/feature_logs')
    parser.add_argument('--output', default=str(package_dir() / 'models' / 'risk_model.joblib'))
    parser.add_argument('--use-seed', action='store_true', help='Use built-in seed dataset. Only for pipeline testing.')
    parser.add_argument('--mix-seed', action='store_true', help='Mix seed data with real data. Useful while data is still small.')
    args = parser.parse_args()

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix
    import joblib

    X_list, y_list = load_csv_data(Path(args.data_dir))
    X_real = np.asarray(X_list, dtype=float) if X_list else np.empty((0, len(FEATURE_NAMES)))
    y_real = np.asarray(y_list) if y_list else np.asarray([])

    if args.use_seed or len(set(y_real)) < 2 or len(y_real) < 30:
        print('WARNING: using built-in seed dataset because real labeled data is missing or too small.')
        print('This model is for pipeline/demo only, not reliable live detection.')
        X, y = seed_dataset()
        trained_with_seed = True
    elif args.mix_seed:
        X_seed, y_seed = seed_dataset()
        X = np.vstack([X_seed, X_real])
        y = np.concatenate([y_seed, y_real])
        trained_with_seed = True
    else:
        X, y = X_real, y_real
        trained_with_seed = False

    print_dataset_summary(y)

    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=7,
        random_state=42,
        class_weight='balanced',
    )

    if len(set(y)) >= 2 and len(y) >= 20:
        # Stratify only if every class has at least 2 samples.
        unique, counts = np.unique(y, return_counts=True)
        can_stratify = bool(np.all(counts >= 2))
        stratify = y if can_stratify else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=stratify
        )
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        print('\nClassification report:')
        print(classification_report(y_test, y_pred))
        print('Confusion matrix labels:', list(clf.classes_))
        print(confusion_matrix(y_test, y_pred, labels=clf.classes_))
    else:
        clf.fit(X, y)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'model': clf,
        'feature_names': FEATURE_NAMES,
        'model_version': 'feature-rf-robot-v1',
        'classes': [str(c) for c in clf.classes_],
    }
    joblib.dump(payload, output)
    meta = {
        'model_version': 'feature-rf-robot-v1',
        'feature_names': FEATURE_NAMES,
        'classes': [str(c) for c in clf.classes_],
        'trained_with_seed_data': bool(trained_with_seed),
        'data_dir': str(Path(args.data_dir).resolve()),
        'note': 'Use real robot-camera logs for reliable performance. Seed-only model is not reliable.',
    }
    output.with_suffix('.json').write_text(json.dumps(meta, indent=2))
    print(f'\nSaved model: {output}')
    print(f'Saved metadata: {output.with_suffix(".json")}')


if __name__ == '__main__':
    main()
