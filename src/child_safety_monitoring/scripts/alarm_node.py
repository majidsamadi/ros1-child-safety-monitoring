#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import struct
import subprocess
import tempfile
import threading
import wave

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import InteractionFeatures, SuspicionEvent


def _generate_alarm_wav(path: str, frequency: float = 880.0, duration: float = 1.5,
                        sample_rate: int = 44100, repeats: int = 3) -> None:
    """Write a repeating sine-wave beep WAV file to *path*."""
    n_samples = int(sample_rate * duration)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for _ in range(repeats):
            for i in range(n_samples):
                # Sine wave with short fade-in/out to avoid clicks
                t = i / sample_rate
                envelope = min(1.0, t * 20, (duration - t) * 20)
                val = int(32767 * envelope * math.sin(2 * math.pi * frequency * t))
                wf.writeframes(struct.pack('<h', val))
            # Short silence between beeps
            wf.writeframes(b'\x00\x00' * int(sample_rate * 0.1))


class AlarmNode:
    def __init__(self):
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        self.last_state = 'unknown'
        self._alarm_proc = None  # currently playing aplay subprocess
        self._alarm_lock = threading.Lock()

        # Pre-generate alarm WAV files once at startup
        self._high_wav = os.path.join(tempfile.gettempdir(), 'csm_high_alarm.wav')
        self._warn_wav = os.path.join(tempfile.gettempdir(), 'csm_warn_alarm.wav')
        _generate_alarm_wav(self._high_wav, frequency=1100.0, duration=0.8, repeats=4)
        _generate_alarm_wav(self._warn_wav, frequency=660.0, duration=0.6, repeats=2)
        rospy.loginfo('Alarm WAV files ready: %s  %s', self._high_wav, self._warn_wav)

        self.pub = rospy.Publisher('/alarm/state', String, queue_size=5, latch=True)
        rospy.Subscriber('/suspicion_event', SuspicionEvent, self.on_event, queue_size=5)
        rospy.Subscriber('/interaction/features', InteractionFeatures, self.on_features, queue_size=5)
        rospy.loginfo('Alarm node started. Publishing /alarm/state')

    def _play_audio(self, wav_path: str) -> None:
        """Play a WAV file non-blockingly via aplay (Linux) in a background thread."""
        def _play():
            with self._alarm_lock:
                # Stop any currently playing alarm first
                if self._alarm_proc and self._alarm_proc.poll() is None:
                    self._alarm_proc.terminate()
                try:
                    self._alarm_proc = subprocess.Popen(
                        ['aplay', '-q', wav_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    # aplay not available — fall back to terminal bell
                    print('\a', end='', flush=True)
        threading.Thread(target=_play, daemon=True).start()

    def publish_state(self, state: str):
        if state == self.last_state:
            return
        self.last_state = state
        self.pub.publish(String(state))

    def on_features(self, msg: InteractionFeatures):
        if msg.suspicion_score < self.normal_threshold:
            self.publish_state('ALARM_OFF')

    def on_event(self, msg: SuspicionEvent):
        level = msg.level.lower()
        if level == 'high':
            self.publish_state('HIGH_ALARM_ON')
            rospy.logerr('[ALARM ON] High-risk suspicious lifting pattern detected')
            self._play_audio(self._high_wav)
        elif level == 'warning':
            self.publish_state('WARNING')
            rospy.logwarn('[ALARM WARNING] Suspicious interaction pattern detected')
            self._play_audio(self._warn_wav)


def main():
    rospy.init_node('alarm_node')
    AlarmNode()
    rospy.spin()


if __name__ == '__main__':
    main()
