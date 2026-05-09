#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict, deque
from typing import Optional, Tuple

import rospy
from child_safety_msgs.msg import InteractionFeatures, PersonPose2D, PersonPose2DArray
from child_safety_monitoring.core.geometry import distance, score_forward, score_inverse
from child_safety_monitoring.core.keypoints import (
    LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP,
    LEFT_WRIST, RIGHT_WRIST, LEFT_ANKLE, RIGHT_ANKLE, LIMBS
)
from child_safety_monitoring.core.scoring import weighted_score, state_from_score

Point = Tuple[float, float]


class InteractionAnalyzerNode:
    def __init__(self):
        self.tracked_topic = rospy.get_param('~tracked_pose_topic', '/poses/tracked')
        self.features_topic = rospy.get_param('~features_topic', '/interaction/features')
        self.history_len = int(rospy.get_param('~history_len', 8))
        self.feet_requires_lift_score = float(rospy.get_param('~feet_requires_lift_score', 0.20))
        self.feet_without_lift_cap = float(rospy.get_param('~feet_without_lift_cap', 0.15))
        self.hist = defaultdict(lambda: deque(maxlen=self.history_len))
        self.pub = rospy.Publisher(self.features_topic, InteractionFeatures, queue_size=5)
        self.sub = rospy.Subscriber(self.tracked_topic, PersonPose2DArray, self.on_tracked, queue_size=5)

    def _point(self, p: PersonPose2D, idx: int) -> Optional[Point]:
        if idx >= len(p.keypoints_xy):
            return None
        if idx < len(p.visible) and not p.visible[idx]:
            return None
        pt = p.keypoints_xy[idx]
        return (float(pt.x), float(pt.y))

    def _bbox_center(self, p: PersonPose2D) -> Point:
        return (p.bbox_x + p.bbox_width / 2.0, p.bbox_y + p.bbox_height / 2.0)

    def _torso_center(self, p: PersonPose2D) -> Point:
        pts = [self._point(p, i) for i in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]]
        pts = [x for x in pts if x is not None]
        if not pts:
            return self._bbox_center(p)
        return (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))

    def _scale(self, p: PersonPose2D) -> float:
        ls = self._point(p, LEFT_SHOULDER)
        rs = self._point(p, RIGHT_SHOULDER)
        shoulder = distance(ls, rs)
        if shoulder < 5 or shoulder > 1e8:
            return max(float(p.bbox_width), 30.0)
        return max(shoulder, 30.0)

    def _wrap_score(self, child: PersonPose2D, adult: PersonPose2D) -> float:
        center = self._torso_center(child)
        scale = self._scale(child)
        wrists = [self._point(adult, LEFT_WRIST), self._point(adult, RIGHT_WRIST)]
        scores = [score_inverse(distance(w, center) / scale, 0.7, 2.0) for w in wrists if w is not None]
        return max(scores) if scores else 0.0

    def _lift_score(self, child: PersonPose2D) -> float:
        center = self._torso_center(child)
        h = self.hist[child.track_id]
        h.append(center)
        if len(h) < 3:
            return 0.0
        dy = h[0][1] - h[-1][1]  # image y decreases when moving upward
        norm = dy / max(float(child.bbox_height), 1.0)
        return score_forward(norm, 0.08, 0.35)

    def _feet_score(self, child: PersonPose2D, lift: float) -> float:
        la = self._point(child, LEFT_ANKLE)
        ra = self._point(child, RIGHT_ANKLE)
        ankles = [p for p in [la, ra] if p is not None]
        if not ankles:
            return 0.0
        lowest_ankle_y = max(y for _, y in ankles)
        bbox_bottom = child.bbox_y + child.bbox_height
        diff = bbox_bottom - lowest_ankle_y
        raw = score_forward(diff / max(float(child.bbox_height), 1.0), 0.18, 0.40)
        if lift >= self.feet_requires_lift_score:
            return raw
        return min(raw, self.feet_without_lift_cap)

    def _limb_motion(self, child: PersonPose2D) -> Tuple[float, float]:
        vals = []
        for idx in LIMBS:
            pt = self._point(child, idx)
            if pt is not None:
                vals.append(pt)
        if not vals:
            return 0.0, 0.0
        avg = (sum(x for x, _ in vals) / len(vals), sum(y for _, y in vals) / len(vals))
        key = child.track_id + '_limb'
        h = self.hist[key]
        h.append(avg)
        if len(h) < 3:
            return 0.0, 0.0
        move = distance(h[-1], h[-2]) / max(float(child.bbox_height), 1.0)
        accel = abs(distance(h[-1], h[-2]) - distance(h[-2], h[-3])) / max(float(child.bbox_height), 1.0)
        return score_forward(move, 0.03, 0.20), score_forward(accel, 0.03, 0.25)

    def on_tracked(self, msg: PersonPose2DArray):
        if len(msg.poses) < 2:
            return

        child = next((p for p in msg.poses if p.size_role == 'smaller_candidate'), None)
        adult = next((p for p in msg.poses if p.size_role == 'larger_candidate'), None)
        if child is None or adult is None:
            sorted_poses = sorted(msg.poses, key=lambda p: p.bbox_height)
            child, adult = sorted_poses[0], sorted_poses[-1]

        child_center = self._torso_center(child)
        adult_center = self._torso_center(adult)
        dist_norm = distance(child_center, adult_center) / self._scale(child)
        contact = score_inverse(dist_norm, 1.0, 2.2)
        wrap = self._wrap_score(child, adult)
        lift = self._lift_score(child)
        feet = self._feet_score(child, lift)
        limb_speed, limb_accel = self._limb_motion(child)
        struggle = max(limb_speed, limb_accel)
        comotion = 0.0
        score = weighted_score(contact, wrap, lift, feet, struggle, comotion)

        out = InteractionFeatures()
        out.header = msg.header
        out.smaller_track_id = child.track_id
        out.larger_track_id = adult.track_id
        out.torso_distance_norm = float(dist_norm)
        out.wrap_score = float(wrap)
        out.lift_score = float(lift)
        out.feet_off_ground_score = float(feet)
        out.limb_speed_score = float(limb_speed)
        out.limb_accel_score = float(limb_accel)
        out.co_motion_score = float(comotion)
        out.suspicion_score = float(score)
        out.state = state_from_score(score)
        self.pub.publish(out)


def main():
    rospy.init_node('interaction_analyzer_node')
    InteractionAnalyzerNode()
    rospy.spin()


if __name__ == '__main__':
    main()
