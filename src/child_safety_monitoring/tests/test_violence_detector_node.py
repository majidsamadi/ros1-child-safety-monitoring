import sys
import types
import pathlib
import importlib.util
import unittest
from unittest.mock import MagicMock
import numpy as np
import torch

# ---------------------------------------------------------------------------
# Stub rospy
# ---------------------------------------------------------------------------
_rospy = types.ModuleType('rospy')
_rospy.get_param = MagicMock(return_value=None)
_rospy.Publisher = MagicMock(return_value=MagicMock())
_rospy.Subscriber = MagicMock(return_value=MagicMock())
_rospy.loginfo = MagicMock()
_rospy.logwarn = MagicMock()
_rospy.logerr = MagicMock()
sys.modules['rospy'] = _rospy

# Stub sensor_msgs
_sm_msg = types.ModuleType('sensor_msgs.msg')
_sm_msg.Image = type('Image', (), {})
_sm = types.ModuleType('sensor_msgs')
_sm.msg = _sm_msg
sys.modules['sensor_msgs'] = _sm
sys.modules['sensor_msgs.msg'] = _sm_msg

# Stub std_msgs
class _Float32:
    def __init__(self, data=0.0):
        self.data = data

_stdm_msg = types.ModuleType('std_msgs.msg')
_stdm_msg.Float32 = _Float32
_stdm = types.ModuleType('std_msgs')
_stdm.msg = _stdm_msg
sys.modules['std_msgs'] = _stdm
sys.modules['std_msgs.msg'] = _stdm_msg

# Stub cv_bridge
class _CvBridgeError(Exception):
    pass

class _CvBridge:
    def __init__(self):
        self.imgmsg_to_cv2 = MagicMock(
            return_value=np.zeros((480, 640, 3), dtype=np.uint8)
        )

_cvb = types.ModuleType('cv_bridge')
_cvb.CvBridge = _CvBridge
_cvb.CvBridgeError = _CvBridgeError
sys.modules['cv_bridge'] = _cvb

# Stub transformers — avoids any network call or model download
_mock_model_output = MagicMock()
_mock_model_output.logits = torch.tensor([[1.0, 5.0]])  # index 1 = "violence" wins

_mock_model_instance = MagicMock()
_mock_model_instance.config.id2label = {0: 'non-violence', 1: 'violence'}
_mock_model_instance.return_value = _mock_model_output

_mock_feature_extractor = MagicMock()
_mock_feature_extractor.return_value = {
    'pixel_values': torch.zeros(1, 3, 224, 224)
}

_transformers = types.ModuleType('transformers')
_transformers.AutoImageProcessor = MagicMock()
_transformers.ViTForImageClassification = MagicMock()
sys.modules['transformers'] = _transformers

# ---------------------------------------------------------------------------
# Load violence_detector_node script via importlib
# ---------------------------------------------------------------------------
_SCRIPT = (
    pathlib.Path(__file__).resolve().parent.parent
    / 'scripts' / 'violence_detector_node.py'
)
_spec = importlib.util.spec_from_file_location('violence_detector_node', _SCRIPT)
_vd_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vd_mod)
ViolenceDetectorNode = _vd_mod.ViolenceDetectorNode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_node(frame_skip=0):
    params = {
        '~image_topic': '/camera/image_raw',
        '~vit_score_topic': '/violence/vit_score',
        '~model_name': 'jaranohaal/vit-base-violence-detection',
        '~frame_skip': frame_skip,
        '~device': 'cpu',
    }
    _rospy.get_param.side_effect = lambda k, d=None: params.get(k, d)
    _rospy.Publisher.reset_mock()
    _rospy.Subscriber.reset_mock()
    _rospy.logwarn.reset_mock()
    _transformers.AutoImageProcessor.from_pretrained = MagicMock(
        return_value=_mock_feature_extractor
    )
    _transformers.ViTForImageClassification.from_pretrained = MagicMock(
        return_value=_mock_model_instance
    )
    _mock_model_instance.side_effect = None  # clear any error stubs from previous tests
    node = ViolenceDetectorNode()
    node.pub = MagicMock()
    return node

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestViolenceDetectorNode(unittest.TestCase):

    def test_violence_idx_found_from_label(self):
        # id2label = {0: 'non-violence', 1: 'violence'} → violence_idx must be 1
        node = _build_node()
        self.assertEqual(node.violence_idx, 1)

    def test_publishes_violence_confidence_on_frame(self):
        node = _build_node(frame_skip=0)
        node.frame_count = 0
        node.on_image(MagicMock())
        self.assertTrue(node.pub.publish.called)
        published = node.pub.publish.call_args[0][0]
        # softmax([1.0, 5.0])[1] ≈ 0.982
        self.assertGreater(published.data, 0.9)

    def test_frame_skip_skips_frames(self):
        node = _build_node(frame_skip=5)
        node.frame_count = 0
        for _ in range(5):
            node.on_image(MagicMock())
        # frames 1-5: none satisfy frame_count % 6 == 0
        node.pub.publish.assert_not_called()

    def test_frame_skip_processes_sixth_frame(self):
        node = _build_node(frame_skip=5)
        node.frame_count = 0
        for _ in range(6):
            node.on_image(MagicMock())
        # frame 6: 6 % 6 == 0 → processed
        self.assertTrue(node.pub.publish.called)

    def test_cvbridge_error_is_caught_and_logged(self):
        node = _build_node(frame_skip=0)
        node.bridge.imgmsg_to_cv2.side_effect = _CvBridgeError('bad encoding')
        node.frame_count = 0
        node.on_image(MagicMock())
        node.pub.publish.assert_not_called()
        _rospy.logwarn.assert_called()

    def test_inference_error_is_caught_and_logged(self):
        node = _build_node(frame_skip=0)
        _mock_model_instance.side_effect = RuntimeError('out of memory')
        node.frame_count = 0
        node.on_image(MagicMock())
        node.pub.publish.assert_not_called()
        _rospy.logwarn.assert_called()


if __name__ == '__main__':
    unittest.main()
