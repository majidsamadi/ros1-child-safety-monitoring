#!/usr/bin/env python3
from __future__ import annotations

import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point32
from child_safety_msgs.msg import PersonPose2D, PersonPose2DArray

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None


class PoseEstimatorNode:
    def __init__(self):
        if YOLO is None:
            raise RuntimeError('ultralytics is not installed. Install requirements_ros1.txt')

        self.image_topic = rospy.get_param('~image_topic', '/camera/image_raw')
        self.raw_pose_topic = rospy.get_param('~raw_pose_topic', '/poses/raw')
        self.annotated_topic = rospy.get_param('~annotated_image_topic', '/camera/pose_overlay')
        self.model_path = rospy.get_param('~model_path', 'yolo11n-pose.pt')
        self.conf = float(rospy.get_param('~confidence_threshold', 0.35))
        self.kpt_conf = float(rospy.get_param('~keypoint_confidence_threshold', 0.25))
        self.device = rospy.get_param('~device', 'cpu')
        self.publish_annotated = bool(rospy.get_param('~publish_annotated', True))
        self.frame_skip = int(rospy.get_param('~frame_skip', 0))
        self.frame_count = 0

        self.bridge = CvBridge()
        self.model = YOLO(self.model_path)
        rospy.loginfo('Loaded YOLO pose model: %s on device=%s', self.model_path, self.device)

        self.pose_pub = rospy.Publisher(self.raw_pose_topic, PersonPose2DArray, queue_size=5)
        self.overlay_pub = rospy.Publisher(self.annotated_topic, Image, queue_size=2)
        self.sub = rospy.Subscriber(self.image_topic, Image, self.on_image, queue_size=1, buff_size=2**24)

    def on_image(self, msg: Image):
        self.frame_count += 1
        if self.frame_skip > 0 and self.frame_count % (self.frame_skip + 1) != 0:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        result = self.model(frame, verbose=False, conf=self.conf, device=self.device)[0]

        arr = PersonPose2DArray()
        arr.header = msg.header

        boxes = []
        if result.boxes is not None and result.boxes.xyxy is not None:
            boxes = result.boxes.xyxy.cpu().numpy().tolist()

        kxy = []
        kcf = []
        if result.keypoints is not None and result.keypoints.xy is not None:
            kxy = result.keypoints.xy.cpu().numpy().tolist()
            if result.keypoints.conf is not None:
                kcf = result.keypoints.conf.cpu().numpy().tolist()

        count = min(len(boxes), len(kxy))
        for i in range(count):
            x1, y1, x2, y2 = boxes[i]
            p = PersonPose2D()
            p.header = msg.header
            p.track_id = ''
            p.size_role = 'unknown'
            p.size_confidence = 0.0
            p.bbox_x = int(x1)
            p.bbox_y = int(y1)
            p.bbox_width = int(max(0.0, x2 - x1))
            p.bbox_height = int(max(0.0, y2 - y1))
            p.center_depth_m = 0.0

            confs = kcf[i] if i < len(kcf) else [1.0] * len(kxy[i])
            for j, pt in enumerate(kxy[i]):
                c = float(confs[j]) if j < len(confs) else 1.0
                p.keypoints_xy.append(Point32(float(pt[0]), float(pt[1]), 0.0))
                p.keypoint_confidence.append(c)
                p.visible.append(c >= self.kpt_conf and pt[0] > 0 and pt[1] > 0)
            arr.poses.append(p)

        self.pose_pub.publish(arr)

        if self.publish_annotated:
            overlay = result.plot()
            out = self.bridge.cv2_to_imgmsg(overlay, encoding='bgr8')
            out.header = msg.header
            self.overlay_pub.publish(out)


def main():
    rospy.init_node('pose_estimator_node')
    PoseEstimatorNode()
    rospy.spin()


if __name__ == '__main__':
    main()
