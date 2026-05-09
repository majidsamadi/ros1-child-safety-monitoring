#!/usr/bin/env python3
from __future__ import annotations

import rospy
from child_safety_msgs.msg import PersonPose2DArray
from child_safety_monitoring.core.centroid_tracker import CentroidTracker


class TrackerNode:
    def __init__(self):
        self.raw_topic = rospy.get_param('~raw_pose_topic', '/poses/raw')
        self.tracked_topic = rospy.get_param('~tracked_pose_topic', '/poses/tracked')
        self.min_people_required = int(rospy.get_param('~min_people_required', 1))
        self.tracker = CentroidTracker(
            max_distance=float(rospy.get_param('~max_track_distance_px', 150.0)),
            max_missed=int(rospy.get_param('~max_missed_frames', 10)),
        )
        self.pub = rospy.Publisher(self.tracked_topic, PersonPose2DArray, queue_size=5)
        self.sub = rospy.Subscriber(self.raw_topic, PersonPose2DArray, self.on_poses, queue_size=5)

    def on_poses(self, msg: PersonPose2DArray):
        if len(msg.poses) < self.min_people_required:
            self.pub.publish(msg)
            return

        detections = []
        for p in msg.poses:
            cx = p.bbox_x + p.bbox_width / 2.0
            cy = p.bbox_y + p.bbox_height / 2.0
            detections.append((cx, cy, float(p.bbox_height)))

        ids = self.tracker.update(detections)
        for p, tid in zip(msg.poses, ids):
            p.track_id = tid

        # Assign smaller/larger roles by bbox height for the current frame.
        if len(msg.poses) >= 2:
            sorted_poses = sorted(msg.poses, key=lambda x: x.bbox_height)
            for p in msg.poses:
                p.size_role = 'bystander'
                p.size_confidence = 0.5
            sorted_poses[0].size_role = 'smaller_candidate'
            sorted_poses[0].size_confidence = 0.8
            sorted_poses[-1].size_role = 'larger_candidate'
            sorted_poses[-1].size_confidence = 0.8

        self.pub.publish(msg)


def main():
    rospy.init_node('tracker_node')
    TrackerNode()
    rospy.spin()


if __name__ == '__main__':
    main()
