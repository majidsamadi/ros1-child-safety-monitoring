#!/usr/bin/env python3
from __future__ import annotations

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction, SuspicionEvent


class AlarmNode:
    """Alarm state node.

    Important: raw AI predictions can be noisy. This node turns warning/high ON
    only from filtered /suspicion_event messages. It uses /risk_model/prediction
    only to turn the alarm OFF when the AI is confidently normal.
    """

    def __init__(self):
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        self.off_probability_threshold = float(rospy.get_param('~off_probability_threshold', 0.75))
        self.last_state = 'unknown'

        self.pub = rospy.Publisher('/alarm/state', String, queue_size=5, latch=True)

        rospy.Subscriber('/risk_model/prediction', RiskPrediction, self.on_prediction, queue_size=5)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features_backup, queue_size=5)

        rospy.loginfo('Alarm node started. Publishing /alarm/state')

    def publish_state(self, state: str):
        if state == self.last_state:
            return
        self.last_state = state
        self.pub.publish(String(state))

        if state == 'HIGH_ALARM_ON':
            rospy.logerr('[ALARM ON] High-risk suspicious movement pattern detected')
        elif state == 'WARNING':
            rospy.logwarn('[ALARM WARNING] Suspicious interaction pattern detected')
        elif state == 'ALARM_OFF':
            rospy.loginfo('[ALARM OFF] Monitoring normally')

    def on_prediction(self, msg: RiskPrediction):
        # Do not turn ON from raw predictions. ai_decision_node filters them.
        if msg.label == 'normal' and msg.probability_normal >= self.off_probability_threshold:
            self.publish_state('ALARM_OFF')

    def on_features_backup(self, msg: InteractionFeatures):
        # Backup mode only for legacy non-AI tests.
        if self.last_state == 'unknown' and msg.suspicion_score < self.normal_threshold:
            self.publish_state('ALARM_OFF')

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower()
        if level == 'high':
            self.publish_state('HIGH_ALARM_ON')
        elif level == 'warning':
            self.publish_state('WARNING')


def main():
    rospy.init_node('alarm_node')
    AlarmNode()
    rospy.spin()


if __name__ == '__main__':
    main()
