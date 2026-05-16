#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import SuspicionEvent


class AlertConsoleNode:
    """Clean console output.

    This node intentionally does NOT print NORMAL messages. It only prints:
      - NEAR SUSPICIOUS
      - HIGH SUSPICIOUS
      - CRITICAL KIDNAPPING RISK
    """

    def __init__(self):
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=10)
        rospy.loginfo('Alert console started. Normal messages are hidden. Waiting for suspicious events...')

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower().strip()
        score = msg.suspicion_score

        if level == 'near':
            rospy.logwarn('[NEAR SUSPICIOUS] risk=%.2f | Something may be starting | %s', score, msg.explanation)
        elif level == 'high':
            rospy.logerr('[HIGH SUSPICIOUS] risk=%.2f | Strong suspicious movement pattern | %s', score, msg.explanation)
        elif level == 'critical':
            rospy.logerr('[CRITICAL KIDNAPPING RISK] risk=%.2f | Immediate human attention required | %s', score, msg.explanation)
        elif level == 'warning':
            # Backward compatibility with old launch files.
            rospy.logwarn('[NEAR SUSPICIOUS] risk=%.2f | %s', score, msg.explanation)
        else:
            # No normal output.
            return


def main():
    rospy.init_node('alert_console_node')
    AlertConsoleNode()
    rospy.spin()


if __name__ == '__main__':
    main()
