#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction, SuspicionEvent


class AlertConsoleNode:
    """Prints clean state-change messages for both rule and AI pipelines."""

    def __init__(self):
        self.last_level = 'unknown'
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        self.warning_probability_threshold = float(rospy.get_param('~warning_probability_threshold', 0.55))
        self.high_probability_threshold = float(rospy.get_param('~high_probability_threshold', 0.75))
        rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features, queue_size=5)
        rospy.Subscriber('/risk_model/prediction', RiskPrediction, self.on_risk, queue_size=5)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.loginfo('Alert console started.')

    def _set_level(self, level: str, message: str, severity: str = 'info'):
        if level == self.last_level:
            return
        self.last_level = level
        if severity == 'error':
            rospy.logerr(message)
        elif severity == 'warn':
            rospy.logwarn(message)
        else:
            rospy.loginfo(message)

    def on_features(self, msg: InteractionFeatures):
        # Used by the original rule-based pipeline and as a normal-state fallback.
        if msg.suspicion_score < self.normal_threshold:
            self._set_level(
                'normal',
                '[NORMAL] score=%.2f | No suspicious interaction pattern detected' % msg.suspicion_score,
                'info',
            )

    def on_risk(self, msg: RiskPrediction):
        label = msg.label.lower().strip()
        if label == 'model_missing':
            self._set_level('model_missing', '[AI MODEL MISSING] Train risk_model.joblib first', 'warn')
            return

        if label == 'high' or msg.probability_high >= self.high_probability_threshold:
            self._set_level(
                'ai_high',
                '[AI HIGH] confidence=%.2f | %s' % (msg.confidence, msg.explanation),
                'error',
            )
        elif label == 'warning' or max(msg.probability_warning, msg.probability_high) >= self.warning_probability_threshold:
            self._set_level(
                'ai_warning',
                '[AI WARNING] confidence=%.2f | %s' % (msg.confidence, msg.explanation),
                'warn',
            )
        elif label == 'normal':
            self._set_level(
                'ai_normal',
                '[AI NORMAL] confidence=%.2f | %s' % (msg.confidence, msg.explanation),
                'info',
            )

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower().strip()
        if level == 'high':
            self._set_level(
                'event_high',
                '[HIGH ALERT] score=%.2f | Suspicious child-lifting pattern detected | %s' % (msg.suspicion_score, msg.explanation),
                'error',
            )
        elif level == 'warning':
            self._set_level(
                'event_warning',
                '[WARNING] score=%.2f | Suspicious interaction pattern detected | %s' % (msg.suspicion_score, msg.explanation),
                'warn',
            )


def main():
    rospy.init_node('alert_console_node')
    AlertConsoleNode()
    rospy.spin()


if __name__ == '__main__':
    main()
