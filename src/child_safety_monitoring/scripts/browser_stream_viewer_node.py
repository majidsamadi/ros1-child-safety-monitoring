#!/usr/bin/env python3
from __future__ import annotations

import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional

import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


latest_jpeg: Optional[bytes] = None
latest_stamp = 0.0
bridge = CvBridge()


def get_robot_ips() -> List[str]:
    ips: List[str] = []

    # Method 1: hostname -I style via socket fallback.
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None):
            ip = item[4][0]
            if "." in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    # Method 2: discover outbound interface IP without sending data.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and ip not in ips:
            ips.append(ip)
    except Exception:
        pass

    return ips or ["127.0.0.1"]


def image_callback(msg: Image) -> None:
    global latest_jpeg, latest_stamp
    try:
        img = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        ok, jpg = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(rospy.get_param("~jpeg_quality", 80))])
        if ok:
            latest_jpeg = jpg.tobytes()
            latest_stamp = time.time()
    except Exception as exc:
        rospy.logwarn("Browser viewer image conversion failed: %s", exc)


class ViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_jpeg

        if self.path in ["/", "/health"]:
            self.send_response(200)
            self.end_headers()
            body = (
                "Robot browser viewer is running.\n"
                "Open /video for MJPEG stream.\n"
                "If /video is blank, check that the selected ROS image topic is publishing.\n"
            )
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path != "/video":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Use /video\n")
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        while not rospy.is_shutdown():
            if latest_jpeg is None:
                time.sleep(0.05)
                continue
            try:
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(latest_jpeg)
                self.wfile.write(b"\r\n")
                time.sleep(0.04)
            except Exception:
                break

    def log_message(self, *_args):
        return


def main() -> None:
    global latest_stamp
    rospy.init_node("browser_stream_viewer_node")

    image_topic = str(rospy.get_param("~image_topic", "/camera/pose_overlay"))
    fallback_topic = str(rospy.get_param("~fallback_image_topic", "/camera/image_raw"))
    port = int(rospy.get_param("~port", 8080))
    host = str(rospy.get_param("~host", "0.0.0.0"))
    fallback_after_seconds = float(rospy.get_param("~fallback_after_seconds", 8.0))

    rospy.Subscriber(image_topic, Image, image_callback, queue_size=1, buff_size=2**24)
    rospy.loginfo("Browser viewer subscribing to %s", image_topic)

    server = ThreadingHTTPServer((host, port), ViewerHandler)

    ips = get_robot_ips()
    rospy.loginfo("Browser viewer started on port %s", port)
    for ip in ips:
        rospy.loginfo("Open browser: http://%s:%s/video", ip, port)

    # Start optional fallback subscriber if overlay does not arrive.
    def maybe_fallback(_event):
        if latest_jpeg is None and fallback_topic and fallback_topic != image_topic:
            rospy.logwarn("No image received on %s yet. Also subscribing to fallback topic %s", image_topic, fallback_topic)
            rospy.Subscriber(fallback_topic, Image, image_callback, queue_size=1, buff_size=2**24)
            maybe_timer.shutdown()

    maybe_timer = rospy.Timer(rospy.Duration(fallback_after_seconds), maybe_fallback, oneshot=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
