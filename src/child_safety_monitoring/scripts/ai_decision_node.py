#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import RiskPrediction, SuspicionEvent


class AIDecisionNode:
    def __init__(self) -> None:
        rospy.init_node('ai_decision_node')
        self.prediction_topic = str(rospy.get_param('~prediction_topic', '/risk_model/prediction'))
        self.warning_threshold = float(rospy.get_param('~warning_threshold', 0.55))
        self.high_threshold = float(rospy.get_param('~high_threshold', 0.75))
        self.warning_persistence = float(rospy.get_param('~warning_persistence_seconds', 0.3))
        self.high_persistence = float(rospy.get_param('~high_persistence_seconds', 0.5))
        self.over_warning_since = None
        self.over_high_since = None
        self.pub = rospy.Publisher('/suspicion_event', SuspicionEvent, queue_size=10)
        self.sub = rospy.Subscriber(self.prediction_topic, RiskPrediction, self.on_prediction, queue_size=10)
        rospy.loginfo('AI decision node started. Waiting for /risk_model/prediction')

    def on_prediction(self, pred: RiskPrediction) -> None:
        now = rospy.Time.now()
        now_sec = now.to_sec()
        p_high = float(pred.probability_high)
        p_warning = max(float(pred.probability_warning), p_high)

        self.over_warning_since = (self.over_warning_since or now_sec) if p_warning >= self.warning_threshold else None
        self.over_high_since = (self.over_high_since or now_sec) if p_high >= self.high_threshold else None

        level = None
        score = 0.0
        if self.over_high_since is not None and (now_sec - self.over_high_since) >= self.high_persistence:
            level = 'high'
            score = p_high
        elif self.over_warning_since is not None and (now_sec - self.over_warning_since) >= self.warning_persistence:
            level = 'warning'
            score = p_warning

        if level is None:
            return

        event = SuspicionEvent()
        event.header = pred.header
        event.event_start = now
        event.current_time = now
        event.level = level
        event.suspicion_score = float(score)
        event.explanation = f'AI {level.upper()} | {pred.explanation}'
        self.pub.publish(event)


def main() -> None:
    AIDecisionNode()
    rospy.spin()


if __name__ == '__main__':
    main()
