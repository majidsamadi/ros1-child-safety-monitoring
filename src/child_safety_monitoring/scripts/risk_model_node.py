#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

import rospy
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction

FEATURE_NAMES = [
    'torso_distance_norm',
    'wrap_score',
    'lift_score',
    'feet_off_ground_score',
    'limb_speed_score',
    'limb_accel_score',
    'co_motion_score',
]


class RiskModelNode:
    """Feature-based AI risk classifier.

    This node is the AI decision layer for Version 1.
    It receives /interaction/features and predicts normal/warning/high.
    """

    def __init__(self) -> None:
        rospy.init_node('risk_model_node')
        self.features_topic = str(rospy.get_param('~features_topic', '/interaction/features'))
        self.prediction_topic = str(rospy.get_param('~prediction_topic', '/risk_model/prediction'))
        self.model_path = str(rospy.get_param('~model_path', self._default_model_path()))
        self.model = None
        self.feature_names: List[str] = FEATURE_NAMES
        self.model_version = 'missing-model'
        self.classes_: List[str] = ['normal', 'warning', 'high']

        self._load_model()

        self.pub = rospy.Publisher(self.prediction_topic, RiskPrediction, queue_size=10)
        self.sub = rospy.Subscriber(self.features_topic, InteractionFeatures, self.on_features, queue_size=10)
        rospy.loginfo('Risk model node started. model_path=%s', self.model_path)

    def _default_model_path(self) -> str:
        # Package path is usually .../src/child_safety_monitoring during development.
        here = Path(__file__).resolve()
        package_dir = here.parent.parent
        return str(package_dir / 'models' / 'risk_model.joblib')

    def _load_model(self) -> None:
        if not os.path.exists(self.model_path):
            rospy.logwarn('Risk model file not found: %s', self.model_path)
            rospy.logwarn('Run: python3 src/child_safety_monitoring/scripts/train_risk_model.py --use-seed')
            return
        try:
            import joblib
            payload = joblib.load(self.model_path)
            if isinstance(payload, dict):
                self.model = payload['model']
                self.feature_names = payload.get('feature_names', FEATURE_NAMES)
                self.model_version = payload.get('model_version', 'risk-model-v1')
            else:
                self.model = payload
                self.model_version = 'risk-model-v1'
            self.classes_ = [str(c) for c in getattr(self.model, 'classes_', self.classes_)]
            rospy.loginfo('Loaded AI risk model: %s', self.model_path)
            rospy.loginfo('Model classes: %s', self.classes_)
        except Exception as exc:
            rospy.logerr('Failed to load risk model: %s', exc)
            self.model = None

    def _features_to_vector(self, msg: InteractionFeatures) -> List[float]:
        # Distance is clipped so one huge value does not dominate the model.
        return [
            min(float(msg.torso_distance_norm), 5.0),
            float(msg.wrap_score),
            float(msg.lift_score),
            float(msg.feet_off_ground_score),
            float(msg.limb_speed_score),
            float(msg.limb_accel_score),
            float(msg.co_motion_score),
        ]

    def on_features(self, msg: InteractionFeatures) -> None:
        pred = RiskPrediction()
        pred.header = msg.header
        pred.model_version = self.model_version

        if self.model is None:
            pred.label = 'model_missing'
            pred.confidence = 0.0
            pred.probability_normal = 1.0
            pred.probability_warning = 0.0
            pred.probability_high = 0.0
            pred.explanation = 'AI model missing. Train risk_model.joblib first.'
            self.pub.publish(pred)
            return

        x = [self._features_to_vector(msg)]
        probs: Dict[str, float] = {'normal': 0.0, 'warning': 0.0, 'high': 0.0}
        label = 'normal'
        confidence = 0.0

        try:
            if hasattr(self.model, 'predict_proba'):
                raw_probs = self.model.predict_proba(x)[0]
                for cls, prob in zip(self.classes_, raw_probs):
                    probs[str(cls)] = float(prob)
                label = max(probs, key=probs.get)
                confidence = float(probs[label])
            else:
                label = str(self.model.predict(x)[0])
                confidence = 1.0
                probs[label] = 1.0
        except Exception as exc:
            rospy.logwarn('Risk model prediction failed: %s', exc)
            return

        pred.label = label
        pred.confidence = confidence
        pred.probability_normal = float(probs.get('normal', 0.0))
        pred.probability_warning = float(probs.get('warning', 0.0))
        pred.probability_high = float(probs.get('high', 0.0))
        pred.explanation = (
            f'AI prediction={label}, confidence={confidence:.2f}, '
            f'p_normal={pred.probability_normal:.2f}, '
            f'p_warning={pred.probability_warning:.2f}, '
            f'p_high={pred.probability_high:.2f}'
        )
        self.pub.publish(pred)


def main() -> None:
    RiskModelNode()
    rospy.spin()


if __name__ == '__main__':
    main()
