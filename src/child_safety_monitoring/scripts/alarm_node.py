#!/usr/bin/env python3
from __future__ import annotations

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import SuspicionEvent


class AlarmNode:
    """Publishes clean alarm states from filtered AI events only.

    No NORMAL console spam. The normal state is still published as ALARM_OFF
    at startup, but it is not repeatedly printed.
    """

    def __init__(self):
        self.last_state = None
        self.pub = rospy.Publisher('/alarm/state', String, queue_size=5, latch=True)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=10)
        rospy.loginfo('Alarm node started. Waiting for filtered AI events...')
        self.publish_state('ALARM_OFF', log=False)

    def publish_state(self, state: str, log: bool = True):
        if state == self.last_state:
            return
        self.last_state = state
        self.pub.publish(String(data=state))

        if not log:
            return
        if state == 'NEAR_SUSPICIOUS':
            rospy.logwarn('[ALARM NEAR] Monitoring suspicious early signal')
        elif state == 'HIGH_SUSPICIOUS':
            rospy.logerr('[ALARM HIGH] High suspicious movement pattern')
        elif state == 'CRITICAL_KIDNAPPING_RISK':
            rospy.logerr('[ALARM CRITICAL] Critical kidnapping risk signal. Human verification required.')

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower().strip()
        if level == 'critical':
            self.publish_state('CRITICAL_KIDNAPPING_RISK')
        elif level == 'high':
            self.publish_state('HIGH_SUSPICIOUS')
        elif level in ('near', 'warning'):
            self.publish_state('NEAR_SUSPICIOUS')


def main():
    rospy.init_node('alarm_node')
    AlarmNode()
    rospy.spin()


if __name__ == '__main__':
    main()
