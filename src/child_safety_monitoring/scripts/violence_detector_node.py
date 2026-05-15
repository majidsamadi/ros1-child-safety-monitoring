#!/usr/bin/env python3
from __future__ import annotations

import rospy
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from std_msgs.msg import Float32

try:
    import torch
    import torch.nn.functional as F
    from PIL import Image as PILImage
    from transformers import ViTFeatureExtractor, ViTForImageClassification
except ImportError as exc:
    raise RuntimeError(
        f'Required packages missing: {exc}. '
        f'Run: pip install -r src/child_safety_monitoring/requirements_ros1.txt'
    )


class ViolenceDetectorNode:
    def __init__(self):
        self.image_topic = rospy.get_param('~image_topic', '/camera/image_raw')
        self.vit_score_topic = rospy.get_param('~vit_score_topic', '/violence/vit_score')
        self.model_name = rospy.get_param('~model_name', 'jaranohaal/vit-base-violence-detection')
        self.frame_skip = int(rospy.get_param('~frame_skip', 5))
        self.device = rospy.get_param('~device', 'cpu')
        self.frame_count = 0
        self.bridge = CvBridge()

        rospy.loginfo('Loading ViT model: %s (device=%s)', self.model_name, self.device)
        try:
            self.feature_extractor = ViTFeatureExtractor.from_pretrained(self.model_name)
            self.model = ViTForImageClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
        except Exception as exc:
            rospy.logerr('Failed to load ViT model %s: %s', self.model_name, exc)
            raise

        self.violence_idx = 0
        for idx, label in self.model.config.id2label.items():
            if label.lower() == 'violence':
                self.violence_idx = idx
                break
        rospy.loginfo('ViT model loaded. violence_idx=%d', self.violence_idx)

        self.pub = rospy.Publisher(self.vit_score_topic, Float32, queue_size=5)
        self.sub = rospy.Subscriber(
            self.image_topic, Image, self.on_image,
            queue_size=1, buff_size=2 ** 24
        )

    def on_image(self, msg: Image):
        self.frame_count += 1
        if self.frame_count % (self.frame_skip + 1) != 0:
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except CvBridgeError as exc:
            rospy.logwarn('CvBridgeError in violence_detector: %s', exc)
            return
        try:
            pil_img = PILImage.fromarray(frame[:, :, ::-1])  # BGR → RGB
            inputs = self.feature_extractor(images=pil_img, return_tensors='pt')
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                logits = self.model(**inputs).logits
            probs = F.softmax(logits, dim=-1)
            violence_conf = float(probs[0, self.violence_idx].item())
            self.pub.publish(Float32(data=violence_conf))
        except Exception as exc:
            rospy.logwarn('ViT inference error: %s', exc)


def main():
    rospy.init_node('violence_detector_node')
    ViolenceDetectorNode()
    rospy.spin()


if __name__ == '__main__':
    main()
