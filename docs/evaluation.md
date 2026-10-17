# Real-video HTTP evaluation

Archive: `open.zip`; expected verdicts: `open/open_labels.xlsx`.
Run: 2026-10-17 13:40:36 +0500. Local model: `qwen3.5:4b`.
Worker SHA-256: `9f580d687d9c579e0d5d7379271b71d235d8eb5575b5fa50ee602f9885bbd8ff`.
Completed: **42/42**. Verdict agreement: **23/42 (54.76%)**.
Maximum upload-to-result time: **77.735 seconds**.

This is agreement on the provided development dataset, not held-out accuracy. No training or
filename/label lookup is performed. Two archive pairs are exact byte duplicates (4/47 and 5/48);
all 42 entries are submitted independently under the neutral filename `recording.mov`.
Every completed response was schema-validated and every evidence JPEG decoded. Videos,
frames, API keys and per-job responses are excluded from this report and Git.

| Video | Expected verdict | Received verdict | Upload-to-result seconds | Error |
| --- | --- | --- | ---: | --- |
| X-1.mov | violation | no_violation | 30.062 | — |
| X-2.mov | violation | violation | 25.891 | — |
| Х-3.mov | no_violation | violation | 27.031 | — |
| Х-4.mov | violation | violation | 50.281 | — |
| Х-5.mov | no_violation | violation | 77.735 | — |
| Х-8.mov | no_violation | no_violation | 54.265 | — |
| Х-10.mov | no_violation | no_violation | 36.407 | — |
| Х-11.mov | violation | violation | 43.515 | — |
| Х-12.mov | no_violation | violation | 75.891 | — |
| Х-13.mov | violation | violation | 67.265 | — |
| Х-14.mov | no_violation | violation | 53.907 | — |
| Х-15.mov | violation | violation | 20.578 | — |
| Х-16.mov | no_violation | no_violation | 22.062 | — |
| Х-17.mov | violation | violation | 16.469 | — |
| Х-18.mov | violation | violation | 23.516 | — |
| Х-19.mov | no_violation | violation | 44.828 | — |
| Х-20.mov | violation | no_violation | 18.000 | — |
| Х-21.mov | no_violation | no_violation | 38.594 | — |
| Х-22.mov | violation | violation | 21.937 | — |
| Х-23.mov | no_violation | violation | 20.391 | — |
| Х-24.mov | violation | violation | 12.828 | — |
| Х-25.mov | no_violation | violation | 49.578 | — |
| Х-26.mov | violation | violation | 15.844 | — |
| Х-27.mov | no_violation | violation | 24.406 | — |
| Х-28.mov | violation | violation | 14.844 | — |
| Х-29.mov | no_violation | violation | 18.922 | — |
| Х-30.mov | violation | no_violation | 22.015 | — |
| Х-31.mov | no_violation | violation | 46.781 | — |
| Х-32.mov | violation | no_violation | 45.641 | — |
| Х-33.mov | violation | violation | 15.297 | — |
| Х-34.mov | violation | violation | 17.828 | — |
| Х-35.mov | no_violation | violation | 38.015 | — |
| Х-37.mov | no_violation | violation | 25.891 | — |
| Х-38.mov | violation | violation | 36.984 | — |
| Х-39.mov | no_violation | violation | 63.188 | — |
| Х-40.mov | violation | violation | 47.000 | — |
| Х-43.mov | no_violation | no_violation | 24.875 | — |
| Х-44.mov | violation | no_violation | 15.797 | — |
| Х-45.mov | no_violation | no_violation | 28.437 | — |
| Х-46.mov | violation | violation | 18.860 | — |
| Х-47.mov | violation | violation | 37.015 | — |
| Х-48.mov | no_violation | violation | 40.016 | — |
