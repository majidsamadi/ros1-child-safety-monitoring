# Live Alert Thresholds

The robot demo now uses an evidence-aware AI decision layer.

The seed Random Forest model can be under-confident during real staged demos, so the decision node combines:

- AI probabilities from `/risk_model/prediction`
- live feature evidence from `/interaction/features`

Output levels:

- `[NEAR SUSPICIOUS]`: early close-contact or low-level risk signal
- `[HIGH SUSPICIOUS]`: strong suspicious movement evidence
- `[CRITICAL KIDNAPPING RISK]`: very strong critical-risk pattern requiring human verification

The system does not prove kidnapping or intent. It detects risk patterns from pose movement.

For critical live testing, use safe adult volunteers or a dummy/mannequin. Do not stage risky lifting with a child.
