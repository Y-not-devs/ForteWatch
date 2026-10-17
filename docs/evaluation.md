# Real-video HTTP evaluation

Archive: `open.zip`; expected verdicts: `open/open_labels.xlsx`.
Run: 2026-10-17 20:02:55 +0500. Local model: `qwen3.5:4b`.
Worker SHA-256: `1f2709fe44cb3518e9d44511bf9e57a442079aa4fb7b10089cd4ed4c162ff0af`.
Pipeline SHA-256 (worker, schemas, rules, service, storage): `c82b445aca1e86ad85cf8cb20530bd0285158015f29db00e5cf47186b8070fd9`.
Completed: **42/42**.
Verdict agreement: **23/42 (54.76%)**.
Maximum upload-to-result time: **73.297 seconds**.

Positive labels: **22/42**.
TP: **17**; TN: **6**;
FP: **14**; FN: **5**; failed: **0**.
Precision: **54.84%**;
end-to-end recall: **77.27%**; F1: **64.15%**.
Nearest-prediction timestamp MAE: **9.527 seconds**, over **17**
positive videos with a prediction.
Within 2 seconds: **7/22**
positive videos (diagnostic threshold, not an official judging tolerance).

Failures count against accuracy and end-to-end recall, and are reported separately from FN.
Localization pairs the single annotated timestamp with the nearest predicted timestamp in
that video, without a distance cutoff. Missed videos are excluded from MAE, not treated as
zero error. This measures temporal proximity only: types are not annotated, so it cannot
establish semantic event matches or classify additional predictions as true/false events.

This is agreement on the provided development dataset, not held-out accuracy. No training or
filename/label lookup is performed. Two archive pairs are exact byte duplicates (4/47 and 5/48);
all 42 entries are submitted independently under the neutral filename `recording.mov`.
Every completed response was schema-validated and every evidence JPEG decoded. Videos,
frames, API keys and per-job responses are excluded from this report and Git.

| Video | Expected verdict | Received verdict | Total seconds | Timestamp error seconds | Error |
| --- | --- | --- | ---: | ---: | --- |
| X-1.mov | violation | no_violation | 32.610 | — | — |
| X-2.mov | violation | violation | 20.390 | 6.233 | — |
| Х-3.mov | no_violation | violation | 20.969 | — | — |
| Х-4.mov | violation | violation | 40.687 | 46.167 | — |
| Х-5.mov | no_violation | violation | 45.110 | — | — |
| Х-8.mov | no_violation | no_violation | 32.469 | — | — |
| Х-10.mov | no_violation | no_violation | 17.734 | — | — |
| Х-11.mov | violation | violation | 42.234 | 6.200 | — |
| Х-12.mov | no_violation | violation | 50.985 | — | — |
| Х-13.mov | violation | violation | 73.297 | 9.500 | — |
| Х-14.mov | no_violation | violation | 57.813 | — | — |
| Х-15.mov | violation | violation | 29.156 | 0.933 | — |
| Х-16.mov | no_violation | no_violation | 25.594 | — | — |
| Х-17.mov | violation | violation | 24.656 | 2.800 | — |
| Х-18.mov | violation | violation | 26.031 | 8.233 | — |
| Х-19.mov | no_violation | violation | 54.687 | — | — |
| Х-20.mov | violation | no_violation | 21.157 | — | — |
| Х-21.mov | no_violation | no_violation | 38.921 | — | — |
| Х-22.mov | violation | violation | 68.250 | 0.333 | — |
| Х-23.mov | no_violation | violation | 50.328 | — | — |
| Х-24.mov | violation | violation | 24.766 | 1.167 | — |
| Х-25.mov | no_violation | violation | 70.390 | — | — |
| Х-26.mov | violation | violation | 29.985 | 0.900 | — |
| Х-27.mov | no_violation | violation | 35.109 | — | — |
| Х-28.mov | violation | violation | 17.406 | 0.233 | — |
| Х-29.mov | no_violation | violation | 18.000 | — | — |
| Х-30.mov | violation | no_violation | 22.453 | — | — |
| Х-31.mov | no_violation | violation | 48.734 | — | — |
| Х-32.mov | violation | no_violation | 45.125 | — | — |
| Х-33.mov | violation | violation | 15.406 | 1.633 | — |
| Х-34.mov | violation | violation | 17.937 | 0.233 | — |
| Х-35.mov | no_violation | violation | 38.110 | — | — |
| Х-37.mov | no_violation | violation | 26.015 | — | — |
| Х-38.mov | violation | violation | 37.891 | 6.667 | — |
| Х-39.mov | no_violation | violation | 64.328 | — | — |
| Х-40.mov | violation | violation | 48.125 | 8.267 | — |
| Х-43.mov | no_violation | no_violation | 25.016 | — | — |
| Х-44.mov | violation | no_violation | 15.985 | — | — |
| Х-45.mov | no_violation | no_violation | 27.547 | — | — |
| Х-46.mov | violation | violation | 18.937 | 5.300 | — |
| Х-47.mov | violation | violation | 36.672 | 57.167 | — |
| Х-48.mov | no_violation | violation | 40.703 | — | — |
