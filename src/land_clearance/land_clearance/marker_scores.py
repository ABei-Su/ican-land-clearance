"""Batch the unchanged 5x5 marker agreement calculation."""
import numpy as np


class MarkerScores:
    def __init__(self, codes):
        self.ids = tuple(codes)
        # Rotating the template instead of the observation gives the same set
        # of four agreements. Stack owns its memory; callers cannot alter it.
        self.rotations = np.stack([
            np.stack([np.rot90(codes[marker_id], k) for k in range(4)])
            for marker_id in self.ids
        ])
        self.rotations.flags.writeable = False

    def scores(self, code):
        agreement = np.mean(self.rotations == code, axis=(-2, -1)).max(axis=1)
        return sorted(zip(agreement.tolist(), self.ids), reverse=True)
