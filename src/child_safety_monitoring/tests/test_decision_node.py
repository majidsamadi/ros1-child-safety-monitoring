import sys
import types
import pathlib
import importlib.util
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub rospy — requires a running ROS master, so mock the whole module
# ---------------------------------------------------------------------------
_time_mock = MagicMock()
_time_mock.to_sec.return_value = 1000.0

_rospy = types.ModuleType('rospy')
_rospy.get_param = MagicMock(return_value=None)
_rospy.Publisher = MagicMock(return_value=MagicMock())
_rospy.Subscriber = MagicMock(return_value=MagicMock())
_rospy.loginfo = MagicMock()
_rospy.logwarn = MagicMock()
_rospy.logerr = MagicMock()
_rospy.Time = MagicMock()
_rospy.Time.now = MagicMock(return_value=_time_mock)
sys.modules['rospy'] = _rospy

# Stub child_safety_msgs
class _InteractionFeatures:
    pass

class _SuspicionEvent:
    pass

_csm_msg = types.ModuleType('child_safety_msgs.msg')
_csm_msg.InteractionFeatures = _InteractionFeatures
_csm_msg.SuspicionEvent = _SuspicionEvent
_csm = types.ModuleType('child_safety_msgs')
_csm.msg = _csm_msg
sys.modules['child_safety_msgs'] = _csm
sys.modules['child_safety_msgs.msg'] = _csm_msg

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

# ---------------------------------------------------------------------------
# Load decision_node script via importlib (avoids sys.path pollution)
# ---------------------------------------------------------------------------
_SCRIPT = (
    pathlib.Path(__file__).resolve().parent.parent
    / 'scripts' / 'decision_node.py'
)
_spec = importlib.util.spec_from_file_location('decision_node', _SCRIPT)
_dn_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dn_mod)
DecisionNode = _dn_mod.DecisionNode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_features(suspicion_score=0.0):
    f = _InteractionFeatures()
    f.header = MagicMock()
    f.suspicion_score = suspicion_score
    f.torso_distance_norm = 0.0
    f.wrap_score = 0.0
    f.lift_score = 0.0
    f.feet_off_ground_score = 0.0
    f.limb_speed_score = 0.0
    f.limb_accel_score = 0.0
    f.co_motion_score = 0.0
    return f


def _build_node(vit_enabled=True, vit_weight=0.5,
                warning_threshold=0.3, high_threshold=0.75):
    params = {
        '~warning_threshold': warning_threshold,
        '~high_threshold': high_threshold,
        '~warning_persistence_seconds': 0.0,
        '~high_persistence_seconds': 0.0,
        '~vit_enabled': vit_enabled,
        '~vit_weight': vit_weight,
        '~vit_score_topic': '/violence/vit_score',
    }
    _rospy.get_param.side_effect = lambda k, d=None: params.get(k, d)
    _rospy.Publisher.reset_mock()
    _rospy.Subscriber.reset_mock()
    _rospy.logwarn.reset_mock()
    node = DecisionNode()
    node.pub = MagicMock()
    return node

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestDecisionNodeFusion(unittest.TestCase):

    def test_fused_score_is_weighted_average(self):
        node = _build_node(vit_enabled=True, vit_weight=0.5, warning_threshold=0.3)
        node.vit_score = 0.8
        node.on_features(_make_features(suspicion_score=0.6))
        event = node.pub.publish.call_args[0][0]
        # fused = 0.5 * 0.6 + 0.5 * 0.8 = 0.70
        self.assertAlmostEqual(event.suspicion_score, 0.70, places=5)

    def test_vit_disabled_uses_raw_pose_score(self):
        node = _build_node(vit_enabled=False, warning_threshold=0.3)
        node.vit_score = 0.99  # should be ignored
        node.on_features(_make_features(suspicion_score=0.5))
        event = node.pub.publish.call_args[0][0]
        self.assertAlmostEqual(event.suspicion_score, 0.5, places=5)

    def test_explanation_includes_vit_score(self):
        node = _build_node(vit_enabled=True, vit_weight=0.5, warning_threshold=0.3)
        node.vit_score = 0.4
        node.on_features(_make_features(suspicion_score=0.6))
        event = node.pub.publish.call_args[0][0]
        self.assertIn('vit_score=0.40', event.explanation)

    def test_on_vit_score_caches_value(self):
        node = _build_node()
        node.on_vit_score(_Float32(data=0.77))
        self.assertAlmostEqual(node.vit_score, 0.77, places=5)

    def test_no_event_published_below_threshold(self):
        node = _build_node(vit_enabled=True, vit_weight=0.5,
                           warning_threshold=0.9, high_threshold=0.95)
        node.vit_score = 0.0
        node.on_features(_make_features(suspicion_score=0.1))
        node.pub.publish.assert_not_called()

    def test_custom_vit_weight(self):
        node = _build_node(vit_enabled=True, vit_weight=0.3, warning_threshold=0.3)
        node.vit_score = 1.0
        node.on_features(_make_features(suspicion_score=0.4))
        event = node.pub.publish.call_args[0][0]
        # fused = 0.7 * 0.4 + 0.3 * 1.0 = 0.58
        self.assertAlmostEqual(event.suspicion_score, 0.58, places=5)


if __name__ == '__main__':
    unittest.main()
