"""Compare saved baseline and current detectors on identical recorded images."""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

import cv2
from land_clearance.markers import MarkerDetector

root = Path(__file__).resolve().parents[1]
directory = root / 'reports/optimization-20261020'
spec = importlib.util.spec_from_file_location('marker_baseline', directory / 'markers_baseline.py')
baseline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = baseline
spec.loader.exec_module(baseline)
assets = root / 'src/land_clearance/assets/markers'
detectors = [baseline.MarkerDetector(assets), MarkerDetector(assets)]
cv2.setNumThreads(1)
images = [cv2.imread(str(p)) for p in sorted((root / 'tests/fixtures').glob('*observation*.png'))]
images += [cv2.imread(str(p)) for p in sorted((root / 'reports/trial-seed29-contacts/mission').glob('*/point-*-aim.png'))]
assert images and all(image is not None for image in images)
timings = [[], []]
for repeat in range(25):
    for frame in images:
        outputs = [None, None]
        # Alternate order to reduce warm-cache bias.
        for index in ((0, 1) if repeat % 2 else (1, 0)):
            started = time.perf_counter()
            found = detectors[index].detect(frame)
            elapsed = time.perf_counter() - started
            if repeat >= 5:
                timings[index].append(elapsed * 1000)
            outputs[index] = [(m.marker_id, m.center.tolist(), m.corners.tolist(), m.confidence) for m in found]
        assert outputs[0] == outputs[1], 'Detector outputs changed'
medians = [statistics.median(values) for values in timings]
result = {
    'images': len(images), 'measured_calls_per_version': len(timings[0]),
    'baseline_median_ms': medians[0], 'optimized_median_ms': medians[1],
    'median_speedup': medians[0] / medians[1],
    'outputs_identical': True,
    'scope': 'Recorded marker images, single OpenCV thread; not full mission speedup',
}
(directory / 'benchmark.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
