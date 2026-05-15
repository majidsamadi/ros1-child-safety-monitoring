# ViT Violence Detection Integration Design

**Date:** 2026-05-15  
**Branch:** violence-detection  
**Status:** Approved

---

## Problem Statement

The existing child safety monitoring pipeline uses YOLO pose estimation + rule-based scoring to produce a `suspicion_score` (0–1). This approach is strong at detecting physical movement patterns (lifting, wrapping, feet-off-ground) but has no semantic understanding of whether the full scene looks violent.

The `jaranohaal/vit-base-violence-detection` model (ViT fine-tuned on the Real Life Violence Situations dataset, 98.8% test accuracy) can classify a full camera frame as `violent` or `non-violent` with a confidence score. Combining this with the existing pose score gives a more robust fused signal that benefits from both spatial/geometric cues and global scene understanding.

---

## Scope

In scope:
- New `violence_detector_node.py` ROS node that runs ViT inference on raw camera frames
- Modified `decision_node.py` that fuses pose-based and ViT-based scores
- Config, launch, and requirements updates
- `vit_enabled` flag for safe fallback when ViT node is not running

Out of scope:
- Replacing the existing pose-based pipeline
- Retraining or fine-tuning the ViT model
- CUDA/GPU inference (CPU only, consistent with existing torch setup)
- Any change to downstream nodes (`alert_console_node`, `alarm_node`)

---

## Architecture

```
/camera/image_raw ──────────────────────────────────────────────────┐
        │                                                            │
        ▼                                                            ▼
pose_estimator_node                                   violence_detector_node  ← NEW
(YOLO → /poses/raw)                                   (ViT → /violence/vit_score)
        │                                                            │
        ▼                                                            │
  tracker_node                                                       │
(/poses/tracked)                                                     │
        │                                                            │
        ▼                                                            │
interaction_analyzer_node                                            │
(/interaction/features)                                              │
        │                                                            │
        └──────────────────────────────────────────────▶ decision_node  ← MODIFIED
                                                         fused_score =
                                                           (1-vit_weight) × suspicion_score
                                                           + vit_weight × vit_score
                                                                │
                                                         /suspicion_event  (unchanged)
                                                                │
                                              alert_console_node + alarm_node  (unchanged)
```

Both `violence_detector_node` and `pose_estimator_node` subscribe to the same `/camera/image_raw` topic independently. They run at different rates: pose estimation processes every frame, ViT skips frames for performance.

---

## Components

### 1. `violence_detector_node.py` (new)

**Responsibility:** Subscribe to raw camera frames, run ViT inference, publish a violence confidence score.

**Inputs:**
- `/camera/image_raw` (`sensor_msgs/Image`)

**Outputs:**
- `/violence/vit_score` (`std_msgs/Float32`, range 0.0–1.0)

**Behaviour:**
1. On startup: load `ViTForImageClassification` and `AutoImageProcessor` from `jaranohaal/vit-base-violence-detection`. Model is downloaded from HuggingFace on first run and cached in `~/.cache/huggingface`. If loading fails, the node logs an error and shuts down cleanly.
2. On each received frame: skip if `frame_count % (frame_skip + 1) != 0`.
3. Convert ROS Image → OpenCV BGR → PIL RGB.
4. Run `AutoImageProcessor` preprocessing (resize to 224×224, normalize).
5. Run `model(**inputs)` under `torch.no_grad()`.
6. Apply softmax to logits; extract confidence of the `"violence"` class.
7. Publish that confidence as `Float32`.

**ROS Parameters (`~` namespace):**

| Parameter | Default | Description |
|---|---|---|
| `image_topic` | `/camera/image_raw` | Input image topic |
| `vit_score_topic` | `/violence/vit_score` | Output score topic |
| `model_name` | `jaranohaal/vit-base-violence-detection` | HuggingFace model ID |
| `frame_skip` | `5` | Skip N frames between inferences (process every 6th frame) |
| `device` | `cpu` | Inference device (`cpu` or `cuda`) |

**Performance note:** ViT-base on CPU takes ~300–800ms per frame depending on hardware. A `frame_skip` of 5 limits it to ~1–2 inferences per second at 10fps input, which is acceptable for this use case.

---

### 2. `decision_node.py` (modified)

**Changes:**
- Add `vit_enabled` ROS param (default `true`). When `false`, ViT subscription is skipped and the original `suspicion_score` is used unchanged — existing thresholds remain valid.
- Add `vit_weight` ROS param (default `0.5`).
- Subscribe to `/violence/vit_score` when `vit_enabled=true`; cache latest value in `self.vit_score` (initialised to `0.0`).
- Replace `score = float(f.suspicion_score)` with:
  ```python
  if self.vit_enabled:
      score = (1 - self.vit_weight) * float(f.suspicion_score) + self.vit_weight * self.vit_score
  else:
      score = float(f.suspicion_score)
  ```
- The `explanation` field on `SuspicionEvent` is extended to include `vit_score` for observability.

**Fallback:** If `violence_detector_node` is not running, `self.vit_score` stays `0.0`. With `vit_weight=0.5` the fused score is halved — which would suppress alerts. For this reason `vit_enabled` must be explicitly set to `false` when not running the ViT node, or the operator must accept reduced sensitivity.

---

## Configuration

**`config/detection_params.yaml` additions:**
```yaml
vit_weight: 0.5       # fraction of final score contributed by ViT (0.0–1.0)
vit_enabled: true     # set false to skip ViT fusion entirely
```

**Existing thresholds are unchanged** when `vit_enabled: true`, since the fused score is still in the 0–1 range. However, calibration testing is recommended after integration because the ViT score raises the effective score for genuinely violent scenes and lowers it for neutral scenes.

---

## Launch Files

`violence_detector_node` is added to `jupiter_robot_camera_demo.launch` — the shared inner launch file that is included by both `stream_demo.launch` and the robot launch. It receives the `camera_topic` arg already passed by the outer launch files:

```xml
<node pkg="child_safety_monitoring" type="violence_detector_node.py"
      name="violence_detector_node" output="screen">
  <param name="image_topic" value="$(arg camera_topic)" />
  <param name="frame_skip" value="5" />
  <param name="device" value="cpu" />
</node>
```

`decision_node` already loads `detection_params.yaml`, so the new `vit_weight` and `vit_enabled` params are picked up automatically.

---

## Dependencies

**`requirements_ros1.txt` addition:**
```
transformers==4.40.2
```

Compatible with Python 3.8 (ROS Noetic) and `torch==2.2.2+cpu`. No additional system packages required.

The model weights (~330MB) are downloaded from HuggingFace on first run. In environments without internet access (e.g. offline robot), the model must be pre-downloaded and the `model_name` param pointed at a local path.

---

## Data Flow

```
Frame arrives on /camera/image_raw
        │
violence_detector_node:
    Convert Image → PIL RGB
    AutoImageProcessor (224×224, normalize)
    ViT inference → softmax → violence_confidence
    Publish /violence/vit_score = violence_confidence
        │
decision_node:
    Receive /interaction/features  → suspicion_score (from poses)
    Cache latest /violence/vit_score
    fused = (1 - vit_weight) × suspicion_score + vit_weight × vit_score
    Apply thresholds → level (warning / high)
    Publish /suspicion_event
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| HuggingFace model unavailable at startup | Node logs error, shuts down cleanly |
| ViT node not running (`vit_enabled: true`) | `vit_score` stays 0.0; fused score is halved (operator should set `vit_enabled: false`) |
| ViT node not running (`vit_enabled: false`) | Existing behaviour unchanged |
| Malformed image message | `cv_bridge` exception caught, frame skipped, warning logged |
| ViT inference error (OOM, etc.) | Exception caught, score not published, warning logged |

---

## Testing

- **Unit test `violence_detector_node`:** Mock the model and feature extractor; verify the node publishes the correct Float32 value for a known input image.
- **Unit test `decision_node` fusion:** Provide synthetic `InteractionFeatures` messages with known `suspicion_score` values plus a known `vit_score`; verify the published `SuspicionEvent.suspicion_score` matches the expected weighted average.
- **Manual integration test:** Run the full pipeline with `stream_demo.launch`; verify `/violence/vit_score` appears in `rostopic list` and `/suspicion_event` explanation includes `vit_score`.
- **Fallback test:** Set `vit_enabled: false`; verify score equals raw `suspicion_score` (no fusion).
