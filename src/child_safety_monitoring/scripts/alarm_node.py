#!/usr/bin/env python3
from __future__ import annotations

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import SuspicionEvent


class AlarmNode:
    def __init__(self):
        self.pub = rospy.Publisher('/alarm/state', String, queue_size=5)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.loginfo('Alarm node started. Publishing /alarm/state')

    def on_event(self, msg):
        if msg.level == 'high':
            self.pub.publish(String('HIGH_ALARM_ON'))
            rospy.logerr('[ALARM ON] High-risk suspicious lifting pattern detected')
        elif msg.level == 'warning':
            self.pub.publish(String('WARNING'))
            rospy.logwarn('[ALARM WARNING] Suspicious interaction pattern detected')


def main():
    rospy.init_node('alarm_node')
    AlarmNode()
    rospy.spin()


if __name__ == '__main__':
    main()
