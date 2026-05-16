#!/usr/bin/env python3
from __future__ import annotations

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction, SuspicionEvent


class AlarmNode:
    """Publishes a simple alarm state for both rule-based and AI pipelines.

    The node listens to /suspicion_event for warning/high events. It also listens
    to /risk_model/prediction when the AI pipeline is used. The /interaction/features
    subscription is only used to return the alarm to off after a quiet period.
    """

    def __init__(self):
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        self.warning_probability_threshold = float(rospy.get_param('~warning_probability_threshold', 0.55))
        self.high_probability_threshold = float(rospy.get_param('~high_probability_threshold', 0.75))
        self.normal_probability_threshold = float(rospy.get_param('~normal_probability_threshold', 0.65))
        self.alarm_hold_seconds = float(rospy.get_param('~alarm_hold_seconds', 1.0))
        self.last_state = 'unknown'
        self.last_alert_time = 0.0

        self.pub = rospy.Publisher('/alarm/state', String, queue_size=5, latch=True)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features, queue_size=5)
        rospy.Subscriber('/risk_model/prediction', RiskPrediction, self.on_risk, queue_size=5)
        rospy.loginfo('Alarm node started. Publishing /alarm/state')
        self.publish_state('ALARM_OFF')

    def publish_state(self, state: str):
        if state == self.last_state:
            return
        self.last_state = state
        self.pub.publish(String(state))
        if state == 'HIGH_ALARM_ON':
            rospy.logerr('[ALARM ON] High-risk suspicious pattern detected')
        elif state == 'WARNING':
            rospy.logwarn('[ALARM WARNING] Suspicious interaction pattern detected')
        else:
            rospy.loginfo('[ALARM OFF] Monitoring normally')

    def _recent_alert(self) -> bool:
        return (rospy.Time.now().to_sec() - self.last_alert_time) < self.alarm_hold_seconds

    def on_features(self, msg: InteractionFeatures):
        # Rule-based and non-AI path: return to off only after a short quiet hold.
        if msg.suspicion_score < self.normal_threshold and not self._recent_alert():
            self.publish_state('ALARM_OFF')

    def on_risk(self, msg: RiskPrediction):
        label = msg.label.lower().strip()
        p_high = float(msg.probability_high)
        p_warning = max(float(msg.probability_warning), p_high)
        p_normal = float(msg.probability_normal)

        if label == 'model_missing':
            return

        if label == 'high' or p_high >= self.high_probability_threshold:
            self.last_alert_time = rospy.Time.now().to_sec()
            self.publish_state('HIGH_ALARM_ON')
        elif label == 'warning' or p_warning >= self.warning_probability_threshold:
            self.last_alert_time = rospy.Time.now().to_sec()
            self.publish_state('WARNING')
        elif label == 'normal' and p_normal >= self.normal_probability_threshold and not self._recent_alert():
            self.publish_state('ALARM_OFF')

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower().strip()
        if level == 'high':
            self.last_alert_time = rospy.Time.now().to_sec()
            self.publish_state('HIGH_ALARM_ON')
        elif level == 'warning':
            self.last_alert_time = rospy.Time.now().to_sec()
            self.publish_state('WARNING')


def main():
    rospy.init_node('alarm_node')
    AlarmNode()
    rospy.spin()


if __name__ == '__main__':
    main()
