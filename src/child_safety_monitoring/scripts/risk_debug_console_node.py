#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction


class RiskDebugConsoleNode:
    """Prints compact live diagnostics for robot testing.

    This node is only for tuning/debugging. It helps answer:
      - Are two people tracked?
      - Are interaction features changing?
      - Is the AI model giving any warning/high probability?

    It does not publish alarms.
    """

    def __init__(self):
        rospy.init_node('risk_debug_console_node')

        self.features_topic = rospy.get_param('~features_topic', '/interaction/features')
        self.prediction_topic = rospy.get_param('~prediction_topic', '/risk_model/prediction')
        self.print_rate_hz = float(rospy.get_param('~print_rate_hz', 1.0))
        self.only_print_when_risk_above = float(rospy.get_param('~only_print_when_risk_above', 0.0))

        self.latest_features = None
        self.latest_prediction = None
        self.latest_features_time = 0.0
        self.latest_prediction_time = 0.0

        rospy.Subscriber(self.features_topic, InteractionFeatures, self.on_features, queue_size=5)
        rospy.Subscriber(self.prediction_topic, RiskPrediction, self.on_prediction, queue_size=5)
        rospy.Timer(rospy.Duration(1.0 / max(self.print_rate_hz, 0.1)), self.on_timer)

        rospy.loginfo('Risk debug console started. Printing live features and AI probabilities.')

    def on_features(self, msg):
        self.latest_features = msg
        self.latest_features_time = rospy.Time.now().to_sec()

    def on_prediction(self, msg):
        self.latest_prediction = msg
        self.latest_prediction_time = rospy.Time.now().to_sec()

    def on_timer(self, _event):
        f = self.latest_features
        p = self.latest_prediction
        if f is None and p is None:
            rospy.logwarn('DEBUG: waiting for /interaction/features and /risk_model/prediction...')
            return

        now = rospy.Time.now().to_sec()
        feature_age = now - self.latest_features_time if f is not None else 999.0
        pred_age = now - self.latest_prediction_time if p is not None else 999.0

        if f is None:
            feature_text = 'features=missing'
            feature_score = 0.0
        else:
            feature_score = float(f.suspicion_score)
            feature_text = (
                f'dist={f.torso_distance_norm:.2f} wrap={f.wrap_score:.2f} lift={f.lift_score:.2f} '
                f'feet={f.feet_off_ground_score:.2f} limb={max(f.limb_speed_score, f.limb_accel_score):.2f} '
                f'co={f.co_motion_score:.2f} feat_score={f.suspicion_score:.2f} age={feature_age:.1f}s'
            )

        if p is None:
            pred_text = 'prediction=missing'
            p_risk = 0.0
        else:
            p_risk = max(float(p.probability_warning), float(p.probability_high))
            pred_text = (
                f'label={p.label} conf={p.confidence:.2f} '
                f'pN={p.probability_normal:.2f} pW={p.probability_warning:.2f} pH={p.probability_high:.2f} '
                f'age={pred_age:.1f}s'
            )

        if max(feature_score, p_risk) < self.only_print_when_risk_above:
            return

        rospy.loginfo('DEBUG | %s | %s', feature_text, pred_text)


def main():
    RiskDebugConsoleNode()
    rospy.spin()


if __name__ == '__main__':
    main()
