#!/usr/bin/env python3
from __future__ import annotations

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import InteractionFeatures, SuspicionEvent


class AlarmNode:
    def __init__(self):
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        self.last_state = 'unknown'
        self.pub = rospy.Publisher('/alarm/state', String, queue_size=5, latch=True)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features, queue_size=5)
        rospy.loginfo('Alarm node started. Publishing /alarm/state')

    def publish_state(self, state: str):
        if state == self.last_state:
            return
        self.last_state = state
        self.pub.publish(String(state))

    def on_features(self, msg: InteractionFeatures):
        if msg.suspicion_score < self.normal_threshold:
            self.publish_state('ALARM_OFF')

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower()
        if level == 'high':
            self.publish_state('HIGH_ALARM_ON')
            rospy.logerr('[ALARM ON] High-risk suspicious lifting pattern detected')
        elif level == 'warning':
            self.publish_state('WARNING')
            rospy.logwarn('[ALARM WARNING] Suspicious interaction pattern detected')


def main():
    rospy.init_node('alarm_node')
    AlarmNode()
    rospy.spin()


if __name__ == '__main__':
    main()
