#!/usr/bin/env python3
from __future__ import annotations

from typing import Optional

import rospy
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction, SuspicionEvent


class AIDecisionNode:
    """Conservative AI decision node.

    The risk model can be noisy on real camera data, especially because the seed
    model is trained from synthetic/example features. This node therefore does
    not trust a single weak AI prediction. It requires:

    1. enough AI probability,
    2. enough supporting interaction-feature evidence,
    3. persistence over time,
    4. cooldown between repeated events.
    """

    def __init__(self) -> None:
        rospy.init_node('ai_decision_node')

        self.prediction_topic = str(rospy.get_param('~prediction_topic', '/risk_model/prediction'))
        self.features_topic = str(rospy.get_param('~features_topic', '/interaction/features'))
        self.event_topic = str(rospy.get_param('~event_topic', '/suspicion_event'))

        # Conservative defaults for real robot demos. The previous defaults were
        # too sensitive and allowed p_high around 0.37-0.51 to trigger alarms.
        self.warning_threshold = float(rospy.get_param('~warning_threshold', 0.72))
        self.high_threshold = float(rospy.get_param('~high_threshold', 0.86))
        self.warning_persistence = float(rospy.get_param('~warning_persistence_seconds', 1.0))
        self.high_persistence = float(rospy.get_param('~high_persistence_seconds', 1.5))
        self.cooldown_seconds = float(rospy.get_param('~event_cooldown_seconds', 4.0))

        # Feature gates stop the alarm from firing on weak/noisy model outputs.
        self.max_feature_age_seconds = float(rospy.get_param('~max_feature_age_seconds', 1.0))
        self.min_feature_score_warning = float(rospy.get_param('~min_feature_score_warning', 0.50))
        self.min_feature_score_high = float(rospy.get_param('~min_feature_score_high', 0.65))
        self.min_high_motion_evidence = float(rospy.get_param('~min_high_motion_evidence', 0.45))

        self.over_warning_since: Optional[float] = None
        self.over_high_since: Optional[float] = None
        self.last_event_level: Optional[str] = None
        self.last_event_time = 0.0
        self.latest_features: Optional[InteractionFeatures] = None
        self.latest_features_time = 0.0

        self.pub = rospy.Publisher(self.event_topic, SuspicionEvent, queue_size=10)
        self.pred_sub = rospy.Subscriber(self.prediction_topic, RiskPrediction, self.on_prediction, queue_size=10)
        self.features_sub = rospy.Subscriber(self.features_topic, InteractionFeatures, self.on_features, queue_size=10)

        rospy.loginfo(
            'AI decision node started. warning>=%.2f high>=%.2f, warning_persist=%.1fs high_persist=%.1fs',
            self.warning_threshold,
            self.high_threshold,
            self.warning_persistence,
            self.high_persistence,
        )

    def on_features(self, msg: InteractionFeatures) -> None:
        self.latest_features = msg
        self.latest_features_time = rospy.Time.now().to_sec()

    def _cooldown_active(self, level: str, now_sec: float) -> bool:
        if self.last_event_level != level:
            return False
        return (now_sec - self.last_event_time) < self.cooldown_seconds

    def _feature_summary(self) -> str:
        f = self.latest_features
        if f is None:
            return 'features=missing'
        return (
            f'features: score={f.suspicion_score:.2f}, dist={f.torso_distance_norm:.2f}, '
            f'wrap={f.wrap_score:.2f}, lift={f.lift_score:.2f}, feet={f.feet_off_ground_score:.2f}, '
            f'limb_speed={f.limb_speed_score:.2f}, limb_accel={f.limb_accel_score:.2f}, co_motion={f.co_motion_score:.2f}'
        )

    def _feature_gates(self, now_sec: float):
        f = self.latest_features
        if f is None or (now_sec - self.latest_features_time) > self.max_feature_age_seconds:
            return False, False

        feature_score = float(f.suspicion_score)
        motion_evidence = max(
            float(f.lift_score),
            float(f.feet_off_ground_score),
            float(f.limb_speed_score),
            float(f.limb_accel_score),
            float(f.co_motion_score),
        )

        warning_gate = feature_score >= self.min_feature_score_warning
        high_gate = (
            feature_score >= self.min_feature_score_high
            and motion_evidence >= self.min_high_motion_evidence
        )
        return warning_gate, high_gate

    def on_prediction(self, pred: RiskPrediction) -> None:
        if pred.label in ('model_missing', 'model_error'):
            rospy.logwarn_throttle(5.0, 'AI decision waiting for valid model: %s', pred.explanation)
            return

        now = rospy.Time.now()
        now_sec = now.to_sec()

        p_normal = float(pred.probability_normal)
        p_warning = float(pred.probability_warning)
        p_high = float(pred.probability_high)

        warning_gate, high_gate = self._feature_gates(now_sec)

        high_candidate = p_high >= self.high_threshold and high_gate
        warning_candidate = (
            (p_warning >= self.warning_threshold or p_high >= self.warning_threshold)
            and warning_gate
        )

        if warning_candidate:
            if self.over_warning_since is None:
                self.over_warning_since = now_sec
        else:
            self.over_warning_since = None

        if high_candidate:
            if self.over_high_since is None:
                self.over_high_since = now_sec
        else:
            self.over_high_since = None

        level = None
        score = 0.0
        event_start = now

        if self.over_high_since is not None and (now_sec - self.over_high_since) >= self.high_persistence:
            level = 'high'
            score = p_high
            event_start = rospy.Time.from_sec(self.over_high_since)
        elif self.over_warning_since is not None and (now_sec - self.over_warning_since) >= self.warning_persistence:
            level = 'warning'
            score = max(p_warning, p_high)
            event_start = rospy.Time.from_sec(self.over_warning_since)

        if level is None:
            if p_normal >= 0.70:
                self.last_event_level = 'normal'
            return

        if self._cooldown_active(level, now_sec):
            return

        self.last_event_level = level
        self.last_event_time = now_sec

        event = SuspicionEvent()
        event.header = pred.header
        event.event_start = event_start
        event.current_time = now
        event.level = level
        event.suspicion_score = float(score)
        event.explanation = (
            f'AI {level.upper()} | p_normal={p_normal:.2f}, p_warning={p_warning:.2f}, p_high={p_high:.2f}; '
            f'{self._feature_summary()}'
        )
        self.pub.publish(event)


def main() -> None:
    AIDecisionNode()
    rospy.spin()


if __name__ == '__main__':
    main()
