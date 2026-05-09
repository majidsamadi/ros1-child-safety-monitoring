#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import InteractionFeatures, SuspicionEvent


class AlertConsoleNode:
    def __init__(self):
        self.last_level = 'unknown'
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features, queue_size=5)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.loginfo('Alert console started.')

    def on_features(self, msg):
        if msg.suspicion_score < self.normal_threshold and self.last_level != 'normal':
            self.last_level = 'normal'
            rospy.loginfo('[NORMAL] score=%.2f | No suspicious interaction pattern detected', msg.suspicion_score)

    def on_event(self, msg):
        level = msg.level.lower()
        if level == self.last_level:
            return
        self.last_level = level
        if level == 'high':
            rospy.logerr('[HIGH ALERT] score=%.2f | Suspicious child-lifting pattern detected | %s', msg.suspicion_score, msg.explanation)
        elif level == 'warning':
            rospy.logwarn('[WARNING] score=%.2f | Suspicious interaction pattern detected | %s', msg.suspicion_score, msg.explanation)


def main():
    rospy.init_node('alert_console_node')
    AlertConsoleNode()
    rospy.spin()


if __name__ == '__main__':
    main()
