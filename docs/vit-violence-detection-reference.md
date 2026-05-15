# ViT Violence Detection — Integration Reference

> **Branch:** `violence-detection`
> **Model:** [`jaranohaal/vit-base-violence-detection`](https://huggingface.co/jaranohaal/vit-base-violence-detection)
> **Added:** 2026-05-15

---

## What Was Added

A Vision Transformer (ViT-base) image classifier is integrated as a parallel violence signal alongside the existing YOLO pose analysis. Every 6th camera frame is run through the ViT model; the resulting confidence score is fused with the pose-based `suspicion_score` in `decision_node` using a weighted average.

### New Files

| File | Purpose |
|---|---|
| `scripts/violence_detector_node.py` | New ROS node — subscribes to camera, runs ViT, publishes Float32 score |
| `tests/test_violence_detector_node.py` | 7 TDD tests for the detector node |
| `tests/test_decision_node.py` | 7 TDD tests for the updated decision node |
| `tests/__init__.py` | Makes `tests/` a Python package |

### Modified Files

| File | Change |
|---|---|
| `scripts/decision_node.py` | Added `vit_enabled`, `vit_weight`, `on_vit_score()`, fusion formula |
| `config/detection_params.yaml` | Added `vit_weight: 0.5`, `vit_enabled: true` |
| `requirements_ros1.txt` | Added `transformers==4.40.2` + pinned transitive deps |
| `launch/jupiter_robot_camera_demo.launch` | Added `violence_detector_node` entry |

---

## Architecture

```
/camera/image_raw ──┬──► pose_estimator_node ──► tracker_node ──► interaction_analyzer_node
                    │                                                         │
                    │                                               /interaction/features
                    │                                                         │
                    └──► violence_detector_node                               ▼
                              │                                        decision_node ──► /suspicion_event
                              │  /violence/vit_score                         ▲
                              └─────────────────────────────────────────────►│
                                     Float32 (0.0–1.0)
```

**Fusion formula** (inside `decision_node`):
```
fused_score = (1 - vit_weight) × suspicion_score + vit_weight × vit_score
```
Default: `0.5 × pose_score + 0.5 × vit_score`

---

## First-Time Setup (inside Docker container)

### 1. Install Python dependencies

```bash
pip install transformers==4.40.2 \
            tokenizers==0.19.1 \
            huggingface-hub==0.23.4 \
            safetensors==0.4.3
```

### 2. Verify import

```bash
python -c "from transformers import AutoImageProcessor, ViTForImageClassification; print('OK')"
```

### 3. Build the workspace

```bash
cd /ros1_ws
catkin_make
source devel/setup.bash
```

> **Note:** The ViT model (~330 MB) downloads automatically from HuggingFace on first launch to `~/.cache/huggingface/`. Ensure internet access or pre-cache the model.

---

## Running the Pipeline

```bash
# Start host webcam streamer (on laptop, outside Docker)
python src/child_safety_monitoring/scripts/host_webcam_streamer.py

# Launch full pipeline (inside Docker)
source /ros1_ws/devel/setup.bash
roslaunch child_safety_monitoring stream_demo.launch \
  stream_url:=http://host.docker.internal:8090/video
```

**Expected startup logs:**
```
[INFO] Loading ViT model: jaranohaal/vit-base-violence-detection (device=cpu)
[INFO] ViT model loaded. violence_idx=1 (found=True)
```

---

## Verifying the Integration

### Check ViT score is publishing
```bash
rostopic echo /violence/vit_score
```
Expected: `Float32` values between 0.0 and 1.0, appearing roughly once per second.

### Check fused score in suspicion events
```bash
rostopic echo /suspicion_event
```
Expected: `explanation` field contains `vit_score=0.XX` when an alert fires.

---

## Configuration Reference

All parameters live in `config/detection_params.yaml` and are loaded by `decision_node`:

```yaml
# Existing thresholds (unchanged)
warning_threshold: 0.55         # fused score to trigger WARNING level
high_threshold: 0.75            # fused score to trigger HIGH level
warning_persistence_seconds: 0.3
high_persistence_seconds: 0.5

# ViT fusion params (new)
vit_weight: 0.5                 # 0.0 = ignore ViT entirely, 1.0 = ViT only
vit_enabled: true               # false = bypass ViT entirely, use raw pose score
```

### `violence_detector_node` ROS parameters

| Parameter | Default | Description |
|---|---|---|
| `~image_topic` | `/camera/image_raw` | Input camera topic |
| `~vit_score_topic` | `/violence/vit_score` | Output score topic |
| `~model_name` | `jaranohaal/vit-base-violence-detection` | HuggingFace model ID |
| `~frame_skip` | `5` | Process every Nth+1 frame (5 = every 6th frame) |
| `~device` | `cpu` | `cpu` or `cuda:0` |

### `decision_node` new ROS parameters

| Parameter | Default | Description |
|---|---|---|
| `~vit_enabled` | `true` | Enable/disable ViT fusion |
| `~vit_weight` | `0.5` | ViT contribution weight (0.0–1.0) |
| `~vit_score_topic` | `/violence/vit_score` | Topic to subscribe to for ViT scores |

---

## Tuning Guide

### Adjust ViT influence
```yaml
vit_weight: 0.3   # Lean more on pose (less ViT)
vit_weight: 0.7   # Lean more on ViT (less pose)
```

### Disable ViT (pose-only mode)
```yaml
vit_enabled: false
```
When disabled: `decision_node` skips the ViT subscription entirely and uses the raw `suspicion_score` unchanged. Existing thresholds apply as before.

### Reduce CPU load
```yaml
# In launch file or rosparam set:
frame_skip: 11   # Process every 12th frame instead of every 6th
```

### Use GPU (if available in Docker)
```yaml
device: cuda:0
```

---

## Performance Notes

| Metric | Value |
|---|---|
| Model size | ~330 MB (ViT-base) |
| CPU inference | ~300–800 ms/frame |
| Effective rate (frame_skip=5) | ~1–2 inferences/second at 30fps input |
| First launch | Downloads model; subsequent launches use cache |
| Python version | 3.8 (ROS Noetic default) |
| transformers pin | `==4.40.2` (last version supporting Python 3.8) |

---

## Cold-Start Behaviour

When `vit_enabled: true` but the `violence_detector_node` has not yet published any score (e.g., model is still loading), `decision_node` treats `vit_score` as `None` and falls back to the **raw pose score** for that period. This prevents false suppression of alerts during startup.

Once the first `/violence/vit_score` message arrives, fusion activates automatically.

---

## Disabling ViT in `rosparam` (runtime override)

```bash
rosparam set /decision_node/vit_enabled false
```

Note: Changes take effect only after node restart. For hot-reload, set via the launch file and re-launch.

---

## ROS Topics Summary

| Topic | Type | Direction | Publisher | Subscriber |
|---|---|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | → | `cctv_stream_node` | `pose_estimator_node`, **`violence_detector_node`** |
| `/violence/vit_score` | `std_msgs/Float32` | → | **`violence_detector_node`** | **`decision_node`** |
| `/interaction/features` | `child_safety_msgs/InteractionFeatures` | → | `interaction_analyzer_node` | **`decision_node`** |
| `/suspicion_event` | `child_safety_msgs/SuspicionEvent` | → | **`decision_node`** | `alert_console_node`, `alarm_node` |

Bold = nodes or topics added/modified in this integration.

---

## Git History (this integration)

| SHA | Message |
|---|---|
| `a56a061` | docs: add ViT violence detection integration design spec |
| `790fb6c` | docs: add vit violence detection implementation plan |
| `5037b17` | chore: add transformers dependency and vit config params |
| `a73ae62` | chore: pin transformers transitive deps for Python 3.8 reproducibility |
| `e3a6d89` | feat: add vit fusion to decision_node with tests |
| `c2dd33a` | fix: address decision_node review issues (cold-start, explanation, bool param) |
| `a718957` | fix: extend bool param exclusion for YAML 1.1 aliases (off, n) |
| `b6487df` | feat: add violence_detector_node with vit inference and tests |
| `51ce83d` | fix: violence_detector_node review fixes (chmod, PIL copy, label logwarn, AutoImageProcessor) |
| `4f0e46b` | test: add test for missing violence label logwarn path |
| `0bbd38a` | docs: replace deprecated ViTFeatureExtractor with AutoImageProcessor in specs |
| `6894586` | feat: add violence_detector_node to launch pipeline |
