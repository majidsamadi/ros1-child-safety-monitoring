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
        self.lift_start_norm = float(rospy.get_param('~lift_start_norm', 0.03))
        self.lift_full_norm = float(rospy.get_param('~lift_full_norm', 0.18))
        self.lift_hold_seconds = float(rospy.get_param('~lift_hold_seconds', 1.50))
        self.lift_hold_min_score = float(rospy.get_param('~lift_hold_min_score', 0.25))
        self.struggle_hold_seconds = float(rospy.get_param('~struggle_hold_seconds', 1.00))
        self.struggle_hold_min_score = float(rospy.get_param('~struggle_hold_min_score', 0.30))
        self.min_visible_keypoints = int(rospy.get_param('~min_visible_keypoints', 9))
        self.min_torso_keypoints = int(rospy.get_param('~min_torso_keypoints', 3))
        self.min_bbox_height = float(rospy.get_param('~min_bbox_height', 120.0))
        self.min_bbox_width = float(rospy.get_param('~min_bbox_width', 45.0))
        self.feet_requires_lift_score = float(rospy.get_param('~feet_requires_lift_score', 0.20))
        self.feet_without_lift_cap = float(rospy.get_param('~feet_without_lift_cap', 0.15))
        self.hist = defaultdict(lambda: deque(maxlen=self.history_len))
        self.lift_hold_until = {}
        self.lift_hold_score = {}
        self.struggle_hold_until = {}
        self.struggle_hold_score = {}
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
        """
        Robust lift cue.

        The old version only used torso-center upward motion over a short history.
        In real robot-camera testing, the child track can partially occlude or jump
        during a lift. This version uses both torso center and bounding-box center,
        then holds recent lift evidence briefly so the signal is not lost instantly.
        """
        torso_center = self._torso_center(child)
        bbox_center = self._bbox_center(child)

        torso_key = child.track_id + '_lift_torso'
        bbox_key = child.track_id + '_lift_bbox'

        torso_hist = self.hist[torso_key]
        bbox_hist = self.hist[bbox_key]

        torso_hist.append(torso_center)
        bbox_hist.append(bbox_center)

        def best_upward_norm(history):
            pts = list(history)
            if len(pts) < 2:
                return 0.0

            best_upward_pixels = 0.0
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    # image y decreases when moving upward
                    upward_pixels = pts[i][1] - pts[j][1]
                    if upward_pixels > best_upward_pixels:
                        best_upward_pixels = upward_pixels

            return best_upward_pixels / max(float(child.bbox_height), 1.0)

        torso_norm = best_upward_norm(torso_hist)
        bbox_norm = best_upward_norm(bbox_hist)
        lift_norm = max(torso_norm, bbox_norm)

        raw_score = score_forward(lift_norm, self.lift_start_norm, self.lift_full_norm)

        now = rospy.Time.now().to_sec()
        track_id = child.track_id

        if raw_score >= self.lift_hold_min_score:
            self.lift_hold_until[track_id] = now + self.lift_hold_seconds
            self.lift_hold_score[track_id] = max(raw_score, self.lift_hold_score.get(track_id, 0.0))

        if now <= self.lift_hold_until.get(track_id, 0.0):
            return max(raw_score, self.lift_hold_score.get(track_id, 0.0))

        self.lift_hold_score[track_id] = raw_score
        return raw_score

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

    def _visible_count(self, p: PersonPose2D) -> int:
        return sum(1 for v in p.visible if v)

    def _visible_torso_count(self, p: PersonPose2D) -> int:
        return sum(
            1
            for idx in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]
            if self._point(p, idx) is not None
        )

    def _is_usable_person(self, p: PersonPose2D) -> bool:
        # Ignore partial bodies / noisy detections.
        # This prevents one half-visible person from being treated as two people.
        if p.bbox_width < self.min_bbox_width:
            return False
        if p.bbox_height < self.min_bbox_height:
            return False
        if self._visible_count(p) < self.min_visible_keypoints:
            return False
        if self._visible_torso_count(p) < self.min_torso_keypoints:
            return False
        return True

    def _relative_lift_score(self, child: PersonPose2D, adult: PersonPose2D) -> float:
        """
        Lift cue based on child body height relative to the adult.

        If the child is lifted, the bottom of the child bounding box rises above
        the adult's lower body / floor level. This helps when the short-term
        vertical-motion cue is lost because of tracking jumps or occlusion.
        """
        child_bottom = float(child.bbox_y + child.bbox_height)
        adult_bottom = float(adult.bbox_y + adult.bbox_height)

        clearance_norm = (adult_bottom - child_bottom) / max(float(child.bbox_height), 1.0)

        # 0.10 = small vertical clearance, 0.45 = strong off-ground cue.
        return score_forward(clearance_norm, 0.10, 0.45)

    def on_tracked(self, msg: PersonPose2DArray):
        usable_poses = [p for p in msg.poses if self._is_usable_person(p)]

        if len(usable_poses) < 2:
            return

        child = next((p for p in usable_poses if p.size_role == 'smaller_candidate'), None)
        adult = next((p for p in usable_poses if p.size_role == 'larger_candidate'), None)
        if child is None or adult is None:
            sorted_poses = sorted(usable_poses, key=lambda p: p.bbox_height)
            child, adult = sorted_poses[0], sorted_poses[-1]

        child_center = self._torso_center(child)
        adult_center = self._torso_center(adult)
        dist_norm = distance(child_center, adult_center) / self._scale(child)
        contact = score_inverse(dist_norm, 1.0, 2.2)
        wrap = self._wrap_score(child, adult)
        motion_lift = self._lift_score(child)
        relative_lift = self._relative_lift_score(child, adult)
        lift = max(motion_lift, relative_lift)
        feet = self._feet_score(child, lift)
        limb_speed, limb_accel = self._limb_motion(child)

        # Reduce false lift detection during calm close/hug scenes.
        # If feet are not off-ground and there is no strong motion,
        # do not trust a high lift score caused by noisy keypoints.
        if relative_lift < 0.40 and feet < 0.30 and limb_speed < 0.25 and limb_accel < 0.25:
            lift = min(lift, 0.15)
            feet = self._feet_score(child, lift)

        # Hold short struggle spikes briefly so rapid limb motion is not lost
        # between frames. This helps the final CRITICAL decision see a continuous
        # lift + struggle pattern instead of isolated one-frame spikes.
        raw_struggle = max(limb_speed, limb_accel)
        now_sec = rospy.Time.now().to_sec()
        if raw_struggle >= self.struggle_hold_min_score:
            self.struggle_hold_until[child.track_id] = now_sec + self.struggle_hold_seconds
            self.struggle_hold_score[child.track_id] = max(
                raw_struggle,
                self.struggle_hold_score.get(child.track_id, 0.0)
            )

        if now_sec <= self.struggle_hold_until.get(child.track_id, 0.0):
            held = self.struggle_hold_score.get(child.track_id, raw_struggle)
            limb_speed = max(limb_speed, held)
            limb_accel = max(limb_accel, held)

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
