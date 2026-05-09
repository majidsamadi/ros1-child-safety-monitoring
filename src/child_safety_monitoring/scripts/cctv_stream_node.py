#!/usr/bin/env python3
from __future__ import annotations

import time
import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


class CCTVStreamNode:
    def __init__(self):
        self.stream_url = rospy.get_param('~stream_url', '')
        self.image_topic = rospy.get_param('~image_topic', '/camera/image_raw')
        self.frame_id = rospy.get_param('~camera_frame_id', 'camera')
        self.publish_rate_hz = float(rospy.get_param('~publish_rate_hz', 15.0))
        self.bridge = CvBridge()
        self.pub = rospy.Publisher(self.image_topic, Image, queue_size=5)

    def _source(self):
        if str(self.stream_url).isdigit():
            return int(self.stream_url)
        return self.stream_url

    def run(self):
        rospy.loginfo('Video stream node starting. Publishing to %s', self.image_topic)
        while not rospy.is_shutdown():
            source = self._source()
            rospy.loginfo('Connecting to video source: %s', source)
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                rospy.logwarn('Could not open video source. Retrying...')
                time.sleep(2.0)
                continue
            rospy.loginfo('Video source connected.')
            rate = rospy.Rate(self.publish_rate_hz)
            while not rospy.is_shutdown() and cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    rospy.logwarn('Frame read failed. Reconnecting...')
                    break
                msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                msg.header.stamp = rospy.Time.now()
                msg.header.frame_id = self.frame_id
                self.pub.publish(msg)
                rate.sleep()
            cap.release()


def main():
    rospy.init_node('cctv_stream_node')
    CCTVStreamNode().run()


if __name__ == '__main__':
    main()
