# Live AI Tuning Notes

The seed risk model is only a starter model. It is good for testing the ROS/AI pipeline, but it is not trained enough for real suspicious-action detection.

## What we observed

During live robot tests, some normal/play actions created low-confidence `AI HIGH` or `AI WARNING` outputs. Examples included high predictions around `0.37` to `0.51`. Those are too weak to trigger a real alarm.

## Immediate fix

The AI decision node is now conservative:

- warning probability must be at least `0.72`
- high probability must be at least `0.86`
- warning must persist for `1.0s`
- high must persist for `1.5s`
- high also needs supporting feature evidence
- alarm turns ON only from filtered `/suspicion_event`, not raw AI prediction

## Why real suspicious tests may not trigger yet

The seed model was not trained from enough real robot-camera examples. To improve the model, collect feature logs for:

- normal standing
- normal walking
- normal close standing
- normal hug / normal play
- safe staged suspicious-contact movement
- safe staged lift-like movement with adults or a dummy/mannequin

Do not use risky tests with a child.

## Recommended demo story

For live robot demo:

1. show camera view
2. show YOLO pose overlay
3. show `/risk_model/prediction`
4. show normal activity does not cause false alarm
5. use the AI simulator demo to show warning/high behavior

This is honest and safe while the real model is still being trained.
