#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import InteractionFeatures


class ScenarioSimulatorNode:
    def __init__(self):
        self.pub = rospy.Publisher('/interaction/features', InteractionFeatures, queue_size=5)
        self.rate_hz = float(rospy.get_param('~rate_hz', 5.0))
        self.duration = float(rospy.get_param('~scenario_duration_seconds', 4.0))
        self.order = ['normal', 'warning', 'high']
        self.started = rospy.Time.now().to_sec()
        self.index = 0
        self.last = None

    def make_msg(self, name):
        m = InteractionFeatures()
        m.header.stamp = rospy.Time.now()
        m.header.frame_id = 'simulated_camera'
        m.smaller_track_id = 'child_candidate_1'
        m.larger_track_id = 'adult_candidate_1'
        if name == 'normal':
            vals = (2.5, 0.05, 0.0, 0.0, 0.1, 0.1, 0.05, 0.10, 'normal')
        elif name == 'warning':
            vals = (0.85, 0.55, 0.35, 0.20, 0.45, 0.40, 0.35, 0.62, 'warning')
        else:
            vals = (0.30, 0.90, 0.95, 0.90, 0.95, 0.90, 0.80, 0.92, 'high_alert')
        (m.torso_distance_norm, m.wrap_score, m.lift_score, m.feet_off_ground_score,
         m.limb_speed_score, m.limb_accel_score, m.co_motion_score, m.suspicion_score, m.state) = vals
        return m

    def run(self):
        r = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown():
            now = rospy.Time.now().to_sec()
            if now - self.started >= self.duration:
                self.index = (self.index + 1) % len(self.order)
                self.started = now
            name = self.order[self.index]
            if name != self.last:
                rospy.loginfo('Changed scenario -> %s', name.upper())
                self.last = name
            self.pub.publish(self.make_msg(name))
            r.sleep()


def main():
    rospy.init_node('scenario_simulator_node')
    ScenarioSimulatorNode().run()


if __name__ == '__main__':
    main()
