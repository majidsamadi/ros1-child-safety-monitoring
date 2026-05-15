# ViT Violence Detection Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `jaranohaal/vit-base-violence-detection` (ViT image classifier) into the ROS 1 child safety monitoring pipeline by adding a new `violence_detector_node.py` that publishes a per-frame violence confidence score, then fusing that score with the existing pose-based `suspicion_score` inside `decision_node.py`.

**Architecture:** A new `violence_detector_node` subscribes to `/camera/image_raw`, runs ViT inference every 6th frame (configurable), and publishes a `Float32` violence confidence to `/violence/vit_score`. `decision_node` caches the latest ViT score and computes a weighted average: `fused = (1 - vit_weight) × suspicion_score + vit_weight × vit_score`. A `vit_enabled` param (default `true`) lets operators skip fusion entirely without changing the existing thresholds.

**Tech Stack:** Python 3.8, ROS 1 Noetic, PyTorch 2.2.2 (CPU), HuggingFace Transformers 4.40.2, OpenCV, Pillow, cv_bridge, pytest, unittest.mock

---

## File Map

| Action  | Path |
|---------|------|
| Modify  | `src/child_safety_monitoring/requirements_ros1.txt` |
| Modify  | `src/child_safety_monitoring/config/detection_params.yaml` |
| Create  | `src/child_safety_monitoring/tests/__init__.py` |
| Create  | `src/child_safety_monitoring/tests/test_decision_node.py` |
| Modify  | `src/child_safety_monitoring/scripts/decision_node.py` |
| Create  | `src/child_safety_monitoring/tests/test_violence_detector_node.py` |
| Create  | `src/child_safety_monitoring/scripts/violence_detector_node.py` |
| Modify  | `src/child_safety_monitoring/launch/jupiter_robot_camera_demo.launch` |

---

## Task 1: Add transformers dependency and config values

No tests needed — this is configuration only.

**Files:**
- Modify: `src/child_safety_monitoring/requirements_ros1.txt`
- Modify: `src/child_safety_monitoring/config/detection_params.yaml`

- [ ] **Step 1: Add transformers to requirements**

  Append one line to `src/child_safety_monitoring/requirements_ros1.txt`. The file should end with:
  ```
  ultralytics==8.3.40
  transformers==4.40.2
  ```

- [ ] **Step 2: Add ViT params to config**

  Replace the entire contents of `src/child_safety_monitoring/config/detection_params.yaml`:
  ```yaml
  warning_threshold: 0.55
  high_threshold: 0.75
  warning_persistence_seconds: 0.3
  high_persistence_seconds: 0.5
  vit_weight: 0.5
  vit_enabled: true
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add src/child_safety_monitoring/requirements_ros1.txt \
          src/child_safety_monitoring/config/detection_params.yaml
  git commit -m "chore: add transformers dependency and vit config params"
  ```

---

## Task 2: Install transformers inside the Docker container

Run the following **inside the running ROS Docker container** (not on the host):

- [ ] **Step 1: Install transformers**

  ```bash
  pip install transformers==4.40.2
  ```

  Expected last line: `Successfully installed transformers-4.40.2` (plus huggingface-hub if not already present).

- [ ] **Step 2: Verify import**

  ```bash
  python -c "from transformers import ViTForImageClassification, ViTFeatureExtractor; print('OK')"
  ```

  Expected output: `OK`

---

## Task 3: Implement decision_node fusion (TDD)

**Files:**
- Create: `src/child_safety_monitoring/tests/__init__.py`
- Create: `src/child_safety_monitoring/tests/test_decision_node.py`
- Modify: `src/child_safety_monitoring/scripts/decision_node.py`

- [ ] **Step 1: Create tests package**

  Create `src/child_safety_monitoring/tests/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing tests**

  Create `src/child_safety_monitoring/tests/test_decision_node.py`:

  ```python
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
  ```

- [ ] **Step 3: Run tests — verify they all fail**

  ```bash
  cd /ros1_ws/src/ros1-child-safety-monitoring
  python -m pytest src/child_safety_monitoring/tests/test_decision_node.py -v
  ```

  Expected: All 6 tests **FAIL** with errors like `AttributeError: type object 'DecisionNode' has no attribute 'vit_score'`

- [ ] **Step 4: Implement the fusion in decision_node**

  Replace the entire contents of `src/child_safety_monitoring/scripts/decision_node.py`:

  ```python
  #!/usr/bin/env python3
  from __future__ import annotations

  import rospy
  from std_msgs.msg import Float32
  from child_safety_msgs.msg import InteractionFeatures, SuspicionEvent


  class DecisionNode:
      def __init__(self):
          self.warning_threshold = float(rospy.get_param('~warning_threshold', 0.55))
          self.high_threshold = float(rospy.get_param('~high_threshold', 0.75))
          self.warning_persistence = float(rospy.get_param('~warning_persistence_seconds', 0.3))
          self.high_persistence = float(rospy.get_param('~high_persistence_seconds', 0.5))
          self.vit_enabled = bool(rospy.get_param('~vit_enabled', True))
          self.vit_weight = float(rospy.get_param('~vit_weight', 0.5))
          self.vit_score = 0.0
          self.warning_since = None
          self.high_since = None
          self.pub = rospy.Publisher('/suspicion_event', SuspicionEvent, queue_size=5)
          self.sub = rospy.Subscriber('/interaction/features', InteractionFeatures,
                                      self.on_features, queue_size=5)
          if self.vit_enabled:
              vit_topic = rospy.get_param('~vit_score_topic', '/violence/vit_score')
              self.vit_sub = rospy.Subscriber(vit_topic, Float32,
                                              self.on_vit_score, queue_size=5)

      def on_vit_score(self, msg: Float32):
          self.vit_score = float(msg.data)

      def on_features(self, f: InteractionFeatures):
          now = rospy.Time.now()
          t = now.to_sec()
          if self.vit_enabled:
              score = ((1.0 - self.vit_weight) * float(f.suspicion_score)
                       + self.vit_weight * self.vit_score)
          else:
              score = float(f.suspicion_score)
          self.warning_since = self.warning_since or t if score >= self.warning_threshold else None
          self.high_since = self.high_since or t if score >= self.high_threshold else None
          level = None
          if self.high_since is not None and (t - self.high_since) >= self.high_persistence:
              level = 'high'
          elif self.warning_since is not None and (t - self.warning_since) >= self.warning_persistence:
              level = 'warning'
          if level is None:
              return
          e = SuspicionEvent()
          e.header = f.header
          e.event_start = now
          e.current_time = now
          e.level = level
          e.suspicion_score = score
          e.explanation = (
              f'{level.upper()} score={score:.2f}; '
              f'contact_dist_norm={f.torso_distance_norm:.2f}; wrap={f.wrap_score:.2f}; '
              f'lift={f.lift_score:.2f}; feet={f.feet_off_ground_score:.2f}; '
              f'limb_speed={f.limb_speed_score:.2f}; limb_accel={f.limb_accel_score:.2f}; '
              f'co_motion={f.co_motion_score:.2f}; vit_score={self.vit_score:.2f}'
          )
          self.pub.publish(e)


  def main():
      rospy.init_node('decision_node')
      DecisionNode()
      rospy.spin()


  if __name__ == '__main__':
      main()
  ```

- [ ] **Step 5: Run tests — verify all pass**

  ```bash
  python -m pytest src/child_safety_monitoring/tests/test_decision_node.py -v
  ```

  Expected:
  ```
  PASSED tests/test_decision_node.py::TestDecisionNodeFusion::test_fused_score_is_weighted_average
  PASSED tests/test_decision_node.py::TestDecisionNodeFusion::test_vit_disabled_uses_raw_pose_score
  PASSED tests/test_decision_node.py::TestDecisionNodeFusion::test_explanation_includes_vit_score
  PASSED tests/test_decision_node.py::TestDecisionNodeFusion::test_on_vit_score_caches_value
  PASSED tests/test_decision_node.py::TestDecisionNodeFusion::test_no_event_published_below_threshold
  PASSED tests/test_decision_node.py::TestDecisionNodeFusion::test_custom_vit_weight
  6 passed
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add src/child_safety_monitoring/tests/__init__.py \
          src/child_safety_monitoring/tests/test_decision_node.py \
          src/child_safety_monitoring/scripts/decision_node.py
  git commit -m "feat: add vit fusion to decision_node with tests"
  ```

---

## Task 4: Implement violence_detector_node (TDD)

**Files:**
- Create: `src/child_safety_monitoring/tests/test_violence_detector_node.py`
- Create: `src/child_safety_monitoring/scripts/violence_detector_node.py`

- [ ] **Step 1: Write the failing tests**

  Create `src/child_safety_monitoring/tests/test_violence_detector_node.py`:

  ```python
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
  _transformers.ViTFeatureExtractor = MagicMock()
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
      _transformers.ViTFeatureExtractor.from_pretrained = MagicMock(
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
  ```

- [ ] **Step 2: Run tests — verify they all fail**

  ```bash
  cd /ros1_ws/src/ros1-child-safety-monitoring
  python -m pytest src/child_safety_monitoring/tests/test_violence_detector_node.py -v
  ```

  Expected: All 6 tests **FAIL** with `FileNotFoundError` or `ModuleNotFoundError` (script does not exist yet).

- [ ] **Step 3: Create violence_detector_node.py**

  Create `src/child_safety_monitoring/scripts/violence_detector_node.py`:

  ```python
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
  ```

- [ ] **Step 4: Make the script executable**

  ```bash
  chmod +x src/child_safety_monitoring/scripts/violence_detector_node.py
  ```

- [ ] **Step 5: Run tests — verify all 6 pass**

  ```bash
  python -m pytest src/child_safety_monitoring/tests/test_violence_detector_node.py -v
  ```

  Expected:
  ```
  PASSED tests/test_violence_detector_node.py::TestViolenceDetectorNode::test_violence_idx_found_from_label
  PASSED tests/test_violence_detector_node.py::TestViolenceDetectorNode::test_publishes_violence_confidence_on_frame
  PASSED tests/test_violence_detector_node.py::TestViolenceDetectorNode::test_frame_skip_skips_frames
  PASSED tests/test_violence_detector_node.py::TestViolenceDetectorNode::test_frame_skip_processes_sixth_frame
  PASSED tests/test_violence_detector_node.py::TestViolenceDetectorNode::test_cvbridge_error_is_caught_and_logged
  PASSED tests/test_violence_detector_node.py::TestViolenceDetectorNode::test_inference_error_is_caught_and_logged
  6 passed
  ```

- [ ] **Step 6: Run the full test suite**

  ```bash
  python -m pytest src/child_safety_monitoring/tests/ -v
  ```

  Expected: **12 passed** (6 from each test file).

- [ ] **Step 7: Commit**

  ```bash
  git add src/child_safety_monitoring/tests/test_violence_detector_node.py \
          src/child_safety_monitoring/scripts/violence_detector_node.py
  git commit -m "feat: add violence_detector_node with vit inference and tests"
  ```

---

## Task 5: Update launch file

**Files:**
- Modify: `src/child_safety_monitoring/launch/jupiter_robot_camera_demo.launch`

- [ ] **Step 1: Add violence_detector_node to the inner launch file**

  Replace the entire contents of `src/child_safety_monitoring/launch/jupiter_robot_camera_demo.launch`:

  ```xml
  <launch>
    <arg name="camera_topic" default="/usb_cam/image_raw" />
    <arg name="pose_model" default="yolo11n-pose.pt" />

    <node pkg="child_safety_monitoring" type="pose_estimator_node.py" name="pose_estimator_node" output="screen">
      <param name="image_topic" value="$(arg camera_topic)" />
      <param name="raw_pose_topic" value="/poses/raw" />
      <param name="annotated_image_topic" value="/camera/pose_overlay" />
      <param name="model_path" value="$(arg pose_model)" />
      <param name="device" value="cpu" />
      <param name="confidence_threshold" value="0.35" />
      <param name="keypoint_confidence_threshold" value="0.25" />
      <param name="publish_annotated" value="true" />
    </node>

    <node pkg="child_safety_monitoring" type="tracker_node.py" name="tracker_node" output="screen" />
    <node pkg="child_safety_monitoring" type="interaction_analyzer_node.py" name="interaction_analyzer_node" output="screen" />

    <node pkg="child_safety_monitoring" type="violence_detector_node.py" name="violence_detector_node" output="screen">
      <param name="image_topic" value="$(arg camera_topic)" />
      <param name="frame_skip" value="5" />
      <param name="device" value="cpu" />
    </node>

    <node pkg="child_safety_monitoring" type="decision_node.py" name="decision_node" output="screen">
      <rosparam file="$(find child_safety_monitoring)/config/detection_params.yaml" command="load" />
    </node>
    <node pkg="child_safety_monitoring" type="alert_console_node.py" name="alert_console_node" output="screen" />
    <node pkg="child_safety_monitoring" type="alarm_node.py" name="alarm_node" output="screen" />
  </launch>
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add src/child_safety_monitoring/launch/jupiter_robot_camera_demo.launch
  git commit -m "feat: add violence_detector_node to launch pipeline"
  ```

---

## Task 6: Manual integration verification (inside Docker)

- [ ] **Step 1: Rebuild the catkin workspace**

  ```bash
  cd /ros1_ws
  catkin_make
  source devel/setup.bash
  ```

  Expected: `[100%] Built target child_safety_msgs_generate_messages_py` and `Finished` with no errors.

- [ ] **Step 2: Start the host webcam streamer (on your laptop, outside Docker)**

  ```bash
  python src/child_safety_monitoring/scripts/host_webcam_streamer.py
  ```

  Expected: `Streaming on http://0.0.0.0:8090/video`

- [ ] **Step 3: Launch the full pipeline (inside Docker)**

  ```bash
  source /ros1_ws/devel/setup.bash
  roslaunch child_safety_monitoring stream_demo.launch stream_url:=http://host.docker.internal:8090/video
  ```

  Expected log lines (may take 30–120s on first run while model downloads ~330MB):
  ```
  [INFO] [...]: Loading ViT model: jaranohaal/vit-base-violence-detection (device=cpu)
  [INFO] [...]: ViT model loaded. violence_idx=1
  ```

- [ ] **Step 4: Verify /violence/vit_score is published**

  In a second Docker terminal:
  ```bash
  source /ros1_ws/devel/setup.bash
  rostopic echo /violence/vit_score
  ```

  Expected: `Float32` values between 0.0 and 1.0 appearing roughly once per second.

- [ ] **Step 5: Verify fused score appears in SuspicionEvent explanation**

  ```bash
  rostopic echo /suspicion_event
  ```

  Expected: `explanation` field contains `vit_score=0.XX` when an event fires.

- [ ] **Step 6: Test the vit_enabled=false fallback**

  Temporarily edit `src/child_safety_monitoring/config/detection_params.yaml`, change `vit_enabled: true` to `vit_enabled: false`, then re-launch. Verify:
  - `/violence/vit_score` still publishes (the detector node still runs)
  - `/suspicion_event` explanation no longer contains `vit_score`
  - Scores match the raw `suspicion_score` from `/interaction/features`

  Restore `vit_enabled: true` when done.

- [ ] **Step 7: Final commit**

  ```bash
  git add -A
  git commit -m "docs: mark integration verification complete"
  ```

---

## Summary

After all tasks, the system will have:

1. **`violence_detector_node.py`** — subscribes to `/camera/image_raw`, runs ViT every 6th frame, publishes to `/violence/vit_score`
2. **Modified `decision_node.py`** — fused score = `(1-vit_weight) × pose_score + vit_weight × vit_score`; safe fallback via `vit_enabled: false`
3. **12 unit tests** (6 per node) covering: fusion math, custom weights, disabled fallback, frame-skip logic, CvBridgeError handling, inference error handling
4. **Updated launch + config** — ViT node wired into both laptop and robot modes via `jupiter_robot_camera_demo.launch`
