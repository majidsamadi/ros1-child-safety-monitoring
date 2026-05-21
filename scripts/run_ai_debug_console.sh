#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/.."
source /opt/ros/noetic/setup.bash
source devel/setup.bash

python3 - <<'PY'
import threading
import time

import rospy
from child_safety_msgs.msg import InteractionFeatures, RiskPrediction

latest_features = None
latest_pred = None

def on_features(msg):
    global latest_features
    latest_features = msg

def on_pred(msg):
    global latest_pred
    latest_pred = msg

rospy.init_node('ai_debug_console', anonymous=True)
rospy.Subscriber('/interaction/features', InteractionFeatures, on_features, queue_size=10)
rospy.Subscriber('/risk_model/prediction', RiskPrediction, on_pred, queue_size=10)

print('AI debug console started. Press CTRL+C to stop.')
print('Waiting for /interaction/features and /risk_model/prediction...')

rate = rospy.Rate(1.0)
while not rospy.is_shutdown():
    f = latest_features
    p = latest_pred
    if f is None:
        print('No /interaction/features yet')
    elif p is None:
        print(
            'FEATURES | dist={:.2f} wrap={:.2f} lift={:.2f} feet={:.2f} limb={:.2f}/{:.2f} co={:.2f} score={:.2f} state={}'.format(
                f.torso_distance_norm, f.wrap_score, f.lift_score, f.feet_off_ground_score,
                f.limb_speed_score, f.limb_accel_score, f.co_motion_score,
                f.suspicion_score, f.state
            )
        )
    else:
        print(
            'DEBUG | dist={:.2f} wrap={:.2f} lift={:.2f} feet={:.2f} limb={:.2f}/{:.2f} co={:.2f} feat={:.2f} | label={} conf={:.2f} pN={:.2f} pW={:.2f} pH={:.2f}'.format(
                f.torso_distance_norm, f.wrap_score, f.lift_score, f.feet_off_ground_score,
                f.limb_speed_score, f.limb_accel_score, f.co_motion_score,
                f.suspicion_score,
                p.label, p.confidence, p.probability_normal, p.probability_warning, p.probability_high
            )
        )
    rate.sleep()
PY
