#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import rospy
from child_safety_msgs.msg import InteractionFeatures

FEATURE_COLUMNS = [
    'torso_distance_norm',
    'wrap_score',
    'lift_score',
    'feet_off_ground_score',
    'limb_speed_score',
    'limb_accel_score',
    'co_motion_score',
]


class FeatureLoggerNode:
    def __init__(self) -> None:
        rospy.init_node('feature_logger_node')
        self.label = str(rospy.get_param('~label', 'normal')).strip().lower()
        self.output_dir = Path(str(rospy.get_param('~output_dir', 'data/feature_logs')))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / f'{self.label}_{rospy.Time.now().to_nsec()}.csv'
        self.file = self.output_file.open('w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['stamp', 'label'] + FEATURE_COLUMNS + ['state'])
        self.sub = rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features, queue_size=100)
        rospy.on_shutdown(self.close)
        rospy.loginfo('Feature logger started. label=%s file=%s', self.label, self.output_file)

    def on_features(self, msg: InteractionFeatures) -> None:
        row = [msg.header.stamp.to_sec(), self.label]
        row.extend([float(getattr(msg, name)) for name in FEATURE_COLUMNS])
        row.append(msg.state)
        self.writer.writerow(row)
        self.file.flush()

    def close(self) -> None:
        try:
            self.file.close()
        except Exception:
            pass


def main() -> None:
    FeatureLoggerNode()
    rospy.spin()


if __name__ == '__main__':
    main()
