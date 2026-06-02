#!/usr/bin/env python3

import math
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import wave

import rospy
from std_msgs.msg import String
from child_safety_msgs.msg import SuspicionEvent


class AlarmNode:
    """
    Alarm node.

    Behaviour:
    - Publishes alarm state on /alarm/state
    - Prints terminal logs for NEAR / HIGH / CRITICAL
    - Plays audible alarm only for CRITICAL_KIDNAPPING_RISK
    """

    def __init__(self):
        rospy.init_node("alarm_node")

        self.sound_enabled = rospy.get_param("~sound_enabled", True)
        self.sound_cooldown_seconds = float(rospy.get_param("~sound_cooldown_seconds", 3.0))
        self.beep_repeats = int(rospy.get_param("~beep_repeats", 5))
        self.beep_frequency_hz = int(rospy.get_param("~beep_frequency_hz", 1200))
        self.beep_duration_seconds = float(rospy.get_param("~beep_duration_seconds", 0.25))

        self.last_state = None
        self.last_sound_time = 0.0

        self.pub = rospy.Publisher("/alarm/state", String, queue_size=5, latch=True)
        rospy.Subscriber("/suspicion_event", SuspicionEvent, self.on_event, queue_size=10)

        self.publish_state("ALARM_OFF", log=False)
        rospy.loginfo("Alarm node started. Publishing /alarm/state")

    def publish_state(self, state, log=True):
        self.pub.publish(String(data=state))

        if state == self.last_state:
            return

        self.last_state = state

        if not log:
            return

        if state == "NEAR_SUSPICIOUS":
            rospy.logwarn("[ALARM NEAR] Monitoring suspicious early signal")
        elif state == "HIGH_SUSPICIOUS":
            rospy.logerr("[ALARM HIGH] High suspicious movement pattern")
        elif state == "CRITICAL_KIDNAPPING_RISK":
            rospy.logerr("[ALARM CRITICAL] Critical kidnapping risk signal. Human verification required.")

    def on_event(self, event):
        level = event.level.lower().strip()

        if level == "critical":
            self.publish_state("CRITICAL_KIDNAPPING_RISK")
            self.play_alarm_sound()
        elif level == "high":
            self.publish_state("HIGH_SUSPICIOUS")
        elif level == "near":
            self.publish_state("NEAR_SUSPICIOUS")
        else:
            self.publish_state("ALARM_OFF")

    def play_alarm_sound(self):
        if not self.sound_enabled:
            return

        now = time.time()
        if now - self.last_sound_time < self.sound_cooldown_seconds:
            return

        self.last_sound_time = now

        thread = threading.Thread(target=self._play_alarm_sound_worker, daemon=True)
        thread.start()

    def _play_alarm_sound_worker(self):
        try:
            wav_path = self._create_alarm_wav()

            if shutil.which("aplay"):
                for _ in range(self.beep_repeats):
                    subprocess.run(
                        ["aplay", "-q", wav_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    time.sleep(0.08)
            else:
                # Terminal fallback if robot has no aplay/audio output configured.
                for _ in range(self.beep_repeats):
                    print("\a", end="", flush=True)
                    time.sleep(self.beep_duration_seconds)

        except Exception as exc:
            rospy.logwarn("Could not play alarm sound: %s", exc)

    def _create_alarm_wav(self):
        sample_rate = 44100
        duration = self.beep_duration_seconds
        frequency = self.beep_frequency_hz
        amplitude = 16000

        path = tempfile.gettempdir() + "/child_safety_critical_alarm.wav"

        with wave.open(path, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            total_samples = int(sample_rate * duration)
            for i in range(total_samples):
                value = int(amplitude * math.sin(2.0 * math.pi * frequency * i / sample_rate))
                wav.writeframes(struct.pack("<h", value))

        return path


def main():
    node = AlarmNode()
    rospy.spin()


if __name__ == "__main__":
    main()
