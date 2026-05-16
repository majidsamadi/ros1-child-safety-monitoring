#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import RiskPrediction, SuspicionEvent


class AIDecisionNode:
    """Converts AI risk probabilities into clean human-readable event levels.

    Output levels:
      near      = early attention signal, not an alarm
      high      = strong suspicious movement pattern
      critical  = critical kidnapping-risk pattern, human verification required

    We intentionally do not output "100% kidnapping detected" because no camera
    model can prove intent with certainty. "Critical kidnapping risk" is safer,
    more honest, and still strong enough for a stakeholder demo.
    """

    def __init__(self) -> None:
        rospy.init_node('ai_decision_node')

        self.prediction_topic = str(rospy.get_param('~prediction_topic', '/risk_model/prediction'))
        self.event_topic = str(rospy.get_param('~event_topic', '/suspicion_event'))

        # Sensitivity levels. These are intentionally conservative for robot demo.
        self.near_threshold = float(rospy.get_param('~near_threshold', 0.45))
        self.high_threshold = float(rospy.get_param('~high_threshold', 0.75))
        self.critical_threshold = float(rospy.get_param('~critical_threshold', 0.90))

        # Persistence reduces flicker from one noisy frame.
        self.near_persistence = float(rospy.get_param('~near_persistence_seconds', 0.20))
        self.high_persistence = float(rospy.get_param('~high_persistence_seconds', 0.80))
        self.critical_persistence = float(rospy.get_param('~critical_persistence_seconds', 1.20))

        # Cooldown reduces repeated logs.
        self.near_cooldown = float(rospy.get_param('~near_cooldown_seconds', 2.0))
        self.high_cooldown = float(rospy.get_param('~high_cooldown_seconds', 3.0))
        self.critical_cooldown = float(rospy.get_param('~critical_cooldown_seconds', 5.0))

        self.near_since = None
        self.high_since = None
        self.critical_since = None
        self.last_event_time_by_level = {}

        self.pub = rospy.Publisher(self.event_topic, SuspicionEvent, queue_size=10)
        self.sub = rospy.Subscriber(self.prediction_topic, RiskPrediction, self.on_prediction, queue_size=10)

        rospy.loginfo(
            'AI decision node started. levels: near>=%.2f high>=%.2f critical>=%.2f',
            self.near_threshold,
            self.high_threshold,
            self.critical_threshold,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        if value != value:  # NaN check
            return 0.0
        return max(0.0, min(1.0, float(value)))

    def _cooldown_active(self, level: str, now_sec: float) -> bool:
        last = self.last_event_time_by_level.get(level)
        if last is None:
            return False
        cooldown = {
            'near': self.near_cooldown,
            'high': self.high_cooldown,
            'critical': self.critical_cooldown,
        }.get(level, 2.0)
        return (now_sec - last) < cooldown

    def _publish_event(self, pred: RiskPrediction, level: str, score: float, event_start_sec: float) -> None:
        now = rospy.Time.now()
        now_sec = now.to_sec()
        if self._cooldown_active(level, now_sec):
            return

        self.last_event_time_by_level[level] = now_sec

        event = SuspicionEvent()
        event.header = pred.header
        event.event_start = rospy.Time.from_sec(event_start_sec)
        event.current_time = now
        event.level = level
        event.suspicion_score = float(score)
        event.explanation = (
            f'AI {level.upper()} | '
            f'p_normal={pred.probability_normal:.2f}, '
            f'p_warning={pred.probability_warning:.2f}, '
            f'p_high={pred.probability_high:.2f}, '
            f'label={pred.label}, confidence={pred.confidence:.2f}'
        )
        self.pub.publish(event)

    def on_prediction(self, pred: RiskPrediction) -> None:
        now_sec = rospy.Time.now().to_sec()

        p_warning = self._clamp(pred.probability_warning)
        p_high = self._clamp(pred.probability_high)
        p_risk = max(p_warning, p_high)

        # Near suspicious: warning/high probability begins to rise.
        if p_risk >= self.near_threshold:
            if self.near_since is None:
                self.near_since = now_sec
        else:
            self.near_since = None

        # High suspicious: high probability is strong.
        if p_high >= self.high_threshold:
            if self.high_since is None:
                self.high_since = now_sec
        else:
            self.high_since = None

        # Critical kidnapping risk: very high probability stays high.
        if p_high >= self.critical_threshold:
            if self.critical_since is None:
                self.critical_since = now_sec
        else:
            self.critical_since = None

        # Highest level wins.
        if self.critical_since is not None and (now_sec - self.critical_since) >= self.critical_persistence:
            self._publish_event(pred, 'critical', p_high, self.critical_since)
            return

        if self.high_since is not None and (now_sec - self.high_since) >= self.high_persistence:
            self._publish_event(pred, 'high', p_high, self.high_since)
            return

        if self.near_since is not None and (now_sec - self.near_since) >= self.near_persistence:
            self._publish_event(pred, 'near', p_risk, self.near_since)
            return


def main() -> None:
    AIDecisionNode()
    rospy.spin()


if __name__ == '__main__':
    main()
