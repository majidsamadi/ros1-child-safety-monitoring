#!/usr/bin/env python3
from __future__ import annotations

from typing import Optional

import rospy

from child_safety_msgs.msg import InteractionFeatures, RiskPrediction, SuspicionEvent


class AIDecisionNode:
    """Evidence-aware AI decision layer.

    The seed Random Forest model is useful, but during early robot demos it can
    keep p_high low even when the interaction features show strong movement
    evidence. This node combines both sources:

    - AI probabilities from /risk_model/prediction
    - live interaction evidence from /interaction/features

    It still does not claim to prove kidnapping or intent. It outputs risk levels:

    - near: early suspicious signal
    - high: strong suspicious movement pattern
    - critical: very strong critical risk pattern requiring human attention
    """

    def __init__(self):
        rospy.init_node('ai_decision_node')

        self.prediction_topic = rospy.get_param('~prediction_topic', '/risk_model/prediction')
        self.features_topic = rospy.get_param('~features_topic', '/interaction/features')
        self.event_topic = rospy.get_param('~event_topic', '/suspicion_event')

        # NEAR is intentionally sensitive so live testing gives feedback.
        self.near_probability_threshold = float(rospy.get_param('~near_probability_threshold', 0.70))
        self.near_feature_score_threshold = float(rospy.get_param('~near_feature_score_threshold', 0.35))
        self.near_wrap_threshold = float(rospy.get_param('~near_wrap_threshold', 0.30))
        self.near_distance_threshold = float(rospy.get_param('~near_distance_threshold', 1.80))

        # Probability thresholds are kept for model-based triggering.
        # The evidence path below can also trigger high/critical when live
        # features are strong even if the seed model is under-confident.
        self.high_probability_threshold = float(rospy.get_param('~high_probability_threshold', 0.80))
        self.critical_probability_threshold = float(rospy.get_param('~critical_probability_threshold', 0.90))

        # Evidence thresholds tuned for staged live robot demos.
        self.high_feature_score_threshold = float(rospy.get_param('~high_feature_score_threshold', 0.60))
        self.high_motion_threshold = float(rospy.get_param('~high_motion_threshold', 0.35))
        self.high_wrap_threshold = float(rospy.get_param('~high_wrap_threshold', 0.75))

        self.critical_feature_score_threshold = float(rospy.get_param('~critical_feature_score_threshold', 0.75))
        self.critical_lift_threshold = float(rospy.get_param('~critical_lift_threshold', 0.75))
        self.critical_limb_threshold = float(rospy.get_param('~critical_limb_threshold', 0.70))
        self.critical_accel_threshold = float(rospy.get_param('~critical_accel_threshold', 0.55))

        self.near_persistence = float(rospy.get_param('~near_persistence_seconds', 0.20))
        self.high_persistence = float(rospy.get_param('~high_persistence_seconds', 0.60))
        self.critical_persistence = float(rospy.get_param('~critical_persistence_seconds', 0.50))

        self.near_cooldown = float(rospy.get_param('~near_cooldown_seconds', 2.0))
        self.high_cooldown = float(rospy.get_param('~high_cooldown_seconds', 3.0))
        self.critical_cooldown = float(rospy.get_param('~critical_cooldown_seconds', 5.0))
        self.max_feature_age_seconds = float(rospy.get_param('~max_feature_age_seconds', 1.0))

        self.latest_features: Optional[InteractionFeatures] = None
        self.latest_features_time = 0.0
        self.near_since = None
        self.high_since = None
        self.critical_since = None
        self.last_event_time_by_level = {}

        self.pub = rospy.Publisher(self.event_topic, SuspicionEvent, queue_size=10)
        rospy.Subscriber(self.prediction_topic, RiskPrediction, self.on_prediction, queue_size=10)
        rospy.Subscriber(self.features_topic, InteractionFeatures, self.on_features, queue_size=10)

        rospy.loginfo(
            'AI decision node started. evidence-aware mode: near_feat>=%.2f, high_feat>=%.2f, critical_feat>=%.2f',
            self.near_feature_score_threshold,
            self.high_feature_score_threshold,
            self.critical_feature_score_threshold,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        try:
            value = float(value)
        except Exception:
            return 0.0
        if value != value:
            return 0.0
        return max(0.0, min(1.0, value))

    def on_features(self, msg: InteractionFeatures):
        self.latest_features = msg
        self.latest_features_time = rospy.Time.now().to_sec()

    def _features_fresh(self, now_sec: float) -> bool:
        return self.latest_features is not None and (now_sec - self.latest_features_time) <= self.max_feature_age_seconds

    def _motion_evidence(self) -> float:
        f = self.latest_features
        if f is None:
            return 0.0
        return max(
            self._clamp(f.lift_score),
            self._clamp(f.feet_off_ground_score),
            self._clamp(f.limb_speed_score),
            self._clamp(f.limb_accel_score),
            self._clamp(f.co_motion_score),
        )

    def _near_feature_evidence(self) -> bool:
        f = self.latest_features
        if f is None:
            return False
        return (
            self._clamp(f.suspicion_score) >= self.near_feature_score_threshold
            or self._clamp(f.wrap_score) >= self.near_wrap_threshold
            or float(f.torso_distance_norm) <= self.near_distance_threshold
        )

    def _feature_summary(self) -> str:
        f = self.latest_features
        if f is None:
            return 'features=missing'
        return (
            f'dist={f.torso_distance_norm:.2f}, wrap={f.wrap_score:.2f}, lift={f.lift_score:.2f}, '
            f'feet={f.feet_off_ground_score:.2f}, limb_speed={f.limb_speed_score:.2f}, '
            f'limb_accel={f.limb_accel_score:.2f}, co_motion={f.co_motion_score:.2f}, '
            f'feature_score={f.suspicion_score:.2f}'
        )

    def _cooldown_active(self, level: str, now_sec: float) -> bool:
        last = self.last_event_time_by_level.get(level)
        if last is None:
            return False
        cooldown = {
            'near': self.near_cooldown,
            'high': self.high_cooldown,
            'critical': self.critical_cooldown,
        }.get(level, 2.0)
        return (now_sec - last) < cooldown

    def _publish_event(self, pred: RiskPrediction, level: str, score: float, start_sec: float):
        now = rospy.Time.now()
        now_sec = now.to_sec()
        if self._cooldown_active(level, now_sec):
            return
        self.last_event_time_by_level[level] = now_sec

        event = SuspicionEvent()
        event.header = pred.header
        event.event_start = rospy.Time.from_sec(start_sec)
        event.current_time = now
        event.level = level
        event.suspicion_score = float(score)
        event.explanation = (
            f'AI {level.upper()} | p_normal={pred.probability_normal:.2f}, '
            f'p_warning={pred.probability_warning:.2f}, p_high={pred.probability_high:.2f}; '
            f'{self._feature_summary()}'
        )
        self.pub.publish(event)

    def on_prediction(self, pred: RiskPrediction):
        if pred.label in ('model_missing', 'model_error'):
            rospy.logwarn_throttle(5.0, 'AI decision waiting for valid model: %s', pred.explanation)
            return

        now_sec = rospy.Time.now().to_sec()
        p_warning = self._clamp(pred.probability_warning)
        p_high = self._clamp(pred.probability_high)
        p_risk = max(p_warning, p_high)

        fresh = self._features_fresh(now_sec)
        f = self.latest_features if fresh else None

        feature_score = self._clamp(f.suspicion_score) if f is not None else 0.0
        wrap = self._clamp(f.wrap_score) if f is not None else 0.0
        lift = self._clamp(f.lift_score) if f is not None else 0.0
        limb_speed = self._clamp(f.limb_speed_score) if f is not None else 0.0
        limb_accel = self._clamp(f.limb_accel_score) if f is not None else 0.0
        motion = self._motion_evidence() if f is not None else 0.0

        near_candidate = False

        # NEAR must require real interaction feature evidence.
        # This prevents false alarms from one quiet person or empty/low-evidence frames.
        if f is not None:
            near_candidate = (
                feature_score >= self.near_feature_score_threshold
                and (
                    self._near_feature_evidence()
                    or p_risk >= self.near_probability_threshold
                )
            )
        high_by_probability = p_high >= self.high_probability_threshold and feature_score >= self.high_feature_score_threshold
        high_by_evidence = (
            fresh
            and feature_score >= self.high_feature_score_threshold
            and wrap >= self.high_wrap_threshold
            and motion >= self.high_motion_threshold
        )
        high_candidate = high_by_probability or high_by_evidence

        # CRITICAL is very strong live evidence. This is a risk alert, not proof of kidnapping.
        critical_by_probability = p_high >= self.critical_probability_threshold and feature_score >= self.critical_feature_score_threshold
        critical_by_evidence = (
            fresh
            and feature_score >= self.critical_feature_score_threshold
            and lift >= self.critical_lift_threshold
            and (limb_speed >= self.critical_limb_threshold or limb_accel >= self.critical_accel_threshold)
        )
        critical_candidate = critical_by_probability or critical_by_evidence

        if near_candidate:
            if self.near_since is None:
                self.near_since = now_sec
        else:
            self.near_since = None

        if high_candidate:
            if self.high_since is None:
                self.high_since = now_sec
        else:
            self.high_since = None

        if critical_candidate:
            if self.critical_since is None:
                self.critical_since = now_sec
        else:
            self.critical_since = None

        if self.critical_since is not None and now_sec - self.critical_since >= self.critical_persistence:
            self._publish_event(pred, 'critical', max(p_high, feature_score), self.critical_since)
            return

        if self.high_since is not None and now_sec - self.high_since >= self.high_persistence:
            self._publish_event(pred, 'high', max(p_high, p_warning, feature_score), self.high_since)
            return

        if self.near_since is not None and now_sec - self.near_since >= self.near_persistence:
            self._publish_event(pred, 'near', max(p_risk, feature_score), self.near_since)
            return


def main():
    AIDecisionNode()
    rospy.spin()


if __name__ == '__main__':
    main()
