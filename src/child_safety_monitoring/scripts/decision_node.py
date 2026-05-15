#!/usr/bin/env python3
from __future__ import annotations

import rospy
from std_msgs.msg import Float32
from child_safety_msgs.msg import InteractionFeatures, SuspicionEvent


class DecisionNode:
    def __init__(self):
        self.warning_threshold = float(rospy.get_param('~warning_threshold', 0.55))
        self.high_threshold = float(rospy.get_param('~high_threshold', 0.75))
        self.warning_persistence = float(rospy.get_param('~warning_persistence_seconds', 0.3))
        self.high_persistence = float(rospy.get_param('~high_persistence_seconds', 0.5))
        self.vit_enabled = bool(rospy.get_param('~vit_enabled', True))
        self.vit_weight = float(rospy.get_param('~vit_weight', 0.5))
        self.vit_score = 0.0
        self.warning_since = None
        self.high_since = None
        self.pub = rospy.Publisher('/suspicion_event', SuspicionEvent, queue_size=5)
        self.sub = rospy.Subscriber('/interaction/features', InteractionFeatures,
                                    self.on_features, queue_size=5)
        if self.vit_enabled:
            vit_topic = rospy.get_param('~vit_score_topic', '/violence/vit_score')
            self.vit_sub = rospy.Subscriber(vit_topic, Float32,
                                            self.on_vit_score, queue_size=5)

    def on_vit_score(self, msg: Float32):
        self.vit_score = float(msg.data)

    def on_features(self, f: InteractionFeatures):
        now = rospy.Time.now()
        t = now.to_sec()
        if self.vit_enabled:
            score = ((1.0 - self.vit_weight) * float(f.suspicion_score)
                     + self.vit_weight * self.vit_score)
        else:
            score = float(f.suspicion_score)
        self.warning_since = self.warning_since or t if score >= self.warning_threshold else None
        self.high_since = self.high_since or t if score >= self.high_threshold else None
        level = None
        if self.high_since is not None and (t - self.high_since) >= self.high_persistence:
            level = 'high'
        elif self.warning_since is not None and (t - self.warning_since) >= self.warning_persistence:
            level = 'warning'
        if level is None:
            return
        e = SuspicionEvent()
        e.header = f.header
        e.event_start = now
        e.current_time = now
        e.level = level
        e.suspicion_score = score
        e.explanation = (
            f'{level.upper()} score={score:.2f}; '
            f'contact_dist_norm={f.torso_distance_norm:.2f}; wrap={f.wrap_score:.2f}; '
            f'lift={f.lift_score:.2f}; feet={f.feet_off_ground_score:.2f}; '
            f'limb_speed={f.limb_speed_score:.2f}; limb_accel={f.limb_accel_score:.2f}; '
            f'co_motion={f.co_motion_score:.2f}; vit_score={self.vit_score:.2f}'
        )
        self.pub.publish(e)


def main():
    rospy.init_node('decision_node')
    DecisionNode()
    rospy.spin()


if __name__ == '__main__':
    main()
