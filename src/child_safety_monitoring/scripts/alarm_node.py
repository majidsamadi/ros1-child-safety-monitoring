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
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for _ in range(repeats):
            for i in range(n_samples):
                t = i / sample_rate
                envelope = min(1.0, t * 20, (duration - t) * 20)
                val = int(32767 * envelope * math.sin(2 * math.pi * frequency * t))
                wf.writeframes(struct.pack('<h', val))
            wf.writeframes(b'\x00\x00' * int(sample_rate * 0.1))


def _generate_siren_wav(path: str, freq_low: float = 700.0, freq_high: float = 1400.0,
                        sweep_duration: float = 0.6, cycles: int = 4,
                        sample_rate: int = 44100) -> None:
    """Generate a classic police wail siren (frequency sweep up and down)."""
    n_sweep = int(sample_rate * sweep_duration)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        phase = 0.0
        for _ in range(cycles):
            # Sweep up: freq_low → freq_high
            for i in range(n_sweep):
                t = i / n_sweep  # 0.0 → 1.0
                freq = freq_low + (freq_high - freq_low) * t
                envelope = min(1.0, t * 10, (1.0 - t) * 10 + 0.5)
                phase += 2 * math.pi * freq / sample_rate
                val = int(32767 * min(1.0, envelope) * math.sin(phase))
                wf.writeframes(struct.pack('<h', val))
            # Sweep down: freq_high → freq_low
            for i in range(n_sweep):
                t = i / n_sweep
                freq = freq_high - (freq_high - freq_low) * t
                envelope = min(1.0, t * 10, (1.0 - t) * 10 + 0.5)
                phase += 2 * math.pi * freq / sample_rate
                val = int(32767 * min(1.0, envelope) * math.sin(phase))
                wf.writeframes(struct.pack('<h', val))


class AlarmNode:
    def __init__(self):
        self.normal_threshold = float(rospy.get_param('~normal_threshold', 0.55))
        self.last_state = 'unknown'
        self._alarm_proc = None  # currently playing aplay subprocess
        self._alarm_lock = threading.Lock()

        # Pre-generate alarm WAV files once at startup
        self._high_wav = os.path.join(tempfile.gettempdir(), 'csm_high_alarm.wav')
        self._warn_wav = os.path.join(tempfile.gettempdir(), 'csm_warn_alarm.wav')
        # HIGH ALERT: police siren wail (700 Hz → 1400 Hz sweep, 8 cycles ≈ 10 seconds)
        _generate_siren_wav(self._high_wav, freq_low=700.0, freq_high=1400.0,
                            sweep_duration=0.6, cycles=8)
        # WARNING: fast double-beep pulse, 4 repeats ≈ 3 seconds
        _generate_alarm_wav(self._warn_wav, frequency=960.0, duration=0.35, repeats=4)
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
