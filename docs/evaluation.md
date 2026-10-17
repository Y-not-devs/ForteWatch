# Real-video HTTP evaluation

Inference run: **2026-10-17 13:40:36 +0500**, source commit **93e2864**, local model `qwen3.5:4b`.
Worker SHA-256: `9f580d687d9c579e0d5d7379271b71d235d8eb5575b5fa50ee602f9885bbd8ff`.
Metrics recomputed: **2026-10-17 16:05:40 +0500**.

This report extends the existing 42-video HTTP run with localization and classification
metrics. All saved terminal job responses were revalidated against the API schema, and
all **160** evidence JPEGs were decoded again. Inference and upload-to-result timings
were **not rerun or remeasured** during this recomputation. The detector was restored to
this exact worker version after the rejected experiments below. The progress-polling fix
and UI changes do not change its predictions.

Completed: **42/42**. Verdict agreement: **23/42 (54.76%)**.
TP: **17**; TN: **6**; FP: **14**; FN: **5**;
failed: **0**. Positive labels: **22/42**.
Precision: **54.84%**; recall: **77.27%**;
F1: **64.15%**.
Historical maximum upload-to-result time: **77.735 seconds**.

Nearest-prediction timestamp MAE: **9.527 seconds**, over
**17/22** positive videos with predictions.
Within 2 seconds: **7/22** positive videos; this is a
diagnostic threshold, not an official judging tolerance.

The single annotated timestamp is paired with the nearest prediction without a distance
cutoff. Missed positive videos are excluded from MAE and remain visible in recall. Types
are not annotated, so temporal proximity does not establish a semantic match or score
additional predictions as true/false events. A correct video verdict can still have an
incorrect type, explanation or timestamp.

These are development-set metrics, not held-out accuracy. No training or filename/label
lookup is used by the worker. Duplicate pairs 4/47 and 5/48 are counted independently;
one positive duplicate pair has different annotated timestamps. Every original upload
used the neutral filename `recording.mov`. Videos, frames, API keys and per-job responses
are excluded from Git.

See [evaluation methodology](analyze-api.md#verification) and
[rejected detector experiments](detector-trials.md).

| Video | Expected verdict | Received verdict | Historical total seconds | Timestamp error seconds |
| --- | --- | --- | ---: | ---: |
| X-1.mov | violation | no_violation | 30.062 | — |
| X-2.mov | violation | violation | 25.891 | 6.233 |
| Х-3.mov | no_violation | violation | 27.031 | — |
| Х-4.mov | violation | violation | 50.281 | 46.167 |
| Х-5.mov | no_violation | violation | 77.735 | — |
| Х-8.mov | no_violation | no_violation | 54.265 | — |
| Х-10.mov | no_violation | no_violation | 36.407 | — |
| Х-11.mov | violation | violation | 43.515 | 6.200 |
| Х-12.mov | no_violation | violation | 75.891 | — |
| Х-13.mov | violation | violation | 67.265 | 9.500 |
| Х-14.mov | no_violation | violation | 53.907 | — |
| Х-15.mov | violation | violation | 20.578 | 0.933 |
| Х-16.mov | no_violation | no_violation | 22.062 | — |
| Х-17.mov | violation | violation | 16.469 | 2.800 |
| Х-18.mov | violation | violation | 23.516 | 8.233 |
| Х-19.mov | no_violation | violation | 44.828 | — |
| Х-20.mov | violation | no_violation | 18.000 | — |
| Х-21.mov | no_violation | no_violation | 38.594 | — |
| Х-22.mov | violation | violation | 21.937 | 0.333 |
| Х-23.mov | no_violation | violation | 20.391 | — |
| Х-24.mov | violation | violation | 12.828 | 1.167 |
| Х-25.mov | no_violation | violation | 49.578 | — |
| Х-26.mov | violation | violation | 15.844 | 0.900 |
| Х-27.mov | no_violation | violation | 24.406 | — |
| Х-28.mov | violation | violation | 14.844 | 0.233 |
| Х-29.mov | no_violation | violation | 18.922 | — |
| Х-30.mov | violation | no_violation | 22.015 | — |
| Х-31.mov | no_violation | violation | 46.781 | — |
| Х-32.mov | violation | no_violation | 45.641 | — |
| Х-33.mov | violation | violation | 15.297 | 1.633 |
| Х-34.mov | violation | violation | 17.828 | 0.233 |
| Х-35.mov | no_violation | violation | 38.015 | — |
| Х-37.mov | no_violation | violation | 25.891 | — |
| Х-38.mov | violation | violation | 36.984 | 6.667 |
| Х-39.mov | no_violation | violation | 63.188 | — |
| Х-40.mov | violation | violation | 47.000 | 8.267 |
| Х-43.mov | no_violation | no_violation | 24.875 | — |
| Х-44.mov | violation | no_violation | 15.797 | — |
| Х-45.mov | no_violation | no_violation | 28.437 | — |
| Х-46.mov | violation | violation | 18.860 | 5.300 |
| Х-47.mov | violation | violation | 37.015 | 57.167 |
| Х-48.mov | no_violation | violation | 40.016 | — |

## Current HTTP smoke check

A fresh two-video HTTP check on 2026-10-17 16:08:36 +0500 completed both verdict
paths: one positive and one negative recording. Both matched their development labels;
upload-to-result times were 19.000 and 18.843 seconds. Responses and all
evidence JPEGs were validated. This is a small regression check after restoring the
baseline and fixing polling, not a new 42-video quality measurement.

A fresh browser upload also completed the real UI-to-model pipeline in **12.8 seconds**,
rendering one finding, three decoded evidence JPEGs and its regulatory source link.
