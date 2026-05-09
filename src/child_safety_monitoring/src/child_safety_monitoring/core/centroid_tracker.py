from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, List, Tuple


@dataclass
class Track:
    track_id: str
    centroid: Tuple[float, float]
    bbox_height: float
    missed: int = 0


class CentroidTracker:
    def __init__(self, max_distance: float = 120.0, max_missed: int = 10) -> None:
        self.max_distance = max_distance
        self.max_missed = max_missed
        self.next_id = 1
        self.tracks: Dict[str, Track] = {}

    def update(self, detections: List[Tuple[float, float, float]]) -> List[str]:
        assigned = [None for _ in detections]
        used_tracks = set()

        for det_i, (cx, cy, h) in enumerate(detections):
            best_id = None
            best_dist = self.max_distance
            for tid, tr in self.tracks.items():
                if tid in used_tracks:
                    continue
                d = sqrt((cx - tr.centroid[0]) ** 2 + (cy - tr.centroid[1]) ** 2)
                if d < best_dist:
                    best_dist = d
                    best_id = tid
            if best_id is not None:
                self.tracks[best_id].centroid = (cx, cy)
                self.tracks[best_id].bbox_height = h
                self.tracks[best_id].missed = 0
                used_tracks.add(best_id)
                assigned[det_i] = best_id

        for det_i, (cx, cy, h) in enumerate(detections):
            if assigned[det_i] is None:
                tid = f'track_{self.next_id}'
                self.next_id += 1
                self.tracks[tid] = Track(tid, (cx, cy), h)
                assigned[det_i] = tid

        for tid in list(self.tracks.keys()):
            if tid not in used_tracks and tid not in assigned:
                self.tracks[tid].missed += 1
                if self.tracks[tid].missed > self.max_missed:
                    del self.tracks[tid]

        return [str(x) for x in assigned]
