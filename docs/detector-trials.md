# Detector experiments

The production detector remains at the measured baseline. Two local Qwen3.5-4B
experiments were stopped early and rejected because they increased missed positive
videos. These are diagnostic comparisons on the same development clips, not complete
42-video runs, held-out results or evidence of generalization.

| Variant | Videos | Baseline TP / FN / FP / TN | Trial TP / FN / FP / TN | Baseline recall | Trial recall |
| --- | ---: | --- | --- | ---: | ---: |
| Separate proposal images and visible-fact verification | 14 | 6 / 1 / 4 / 3 | 3 / 4 / 4 / 3 | 85.71% | 42.86% |
| Baseline proposals and visible-fact verification | 9 | 3 / 1 / 3 / 2 | 0 / 4 / 1 / 4 | 75.00% | 0.00% |

The first experiment used up to six individual proposal images with one overlapping
frame, then independently checked the visible facts on three larger images. The second
kept the baseline proposal mosaics and changed only evidence verification. Its source
is retained in commit `40013cb640a81c2957d72e7c7361f055bf94b6b9`; the following commit restores
the baseline worker and schema. The first discarded working-copy variant is identified
only by its worker hash below, not retained as a production implementation.

The strict verifier required explicit visual predicates for each rule and used its own
observation in the output. On the second sample it removed two false-positive videos,
but all four positive videos were missed instead of one. It therefore fails the task's
priority on avoiding missed violations. Neither change is enabled in the final code.

No video, frame, label or description was sent to an external AI API by the tested
service. Labels were read only by the evaluator. Individual job records remain private
under `backend/data/validation`.

A separate attempted run was invalidated by a transient Windows permission error while
reading `progress.json`, followed by busy responses while the job was still running.
That run is excluded from the model comparisons. The final API fix preserves processing
status when the optional progress snapshot is locked; the regression test verifies
polling resumes when the lock clears. The evaluator now aborts on a busy response rather
than publishing a cascade of unprocessed videos as a full run.

## Worker identities

Separate-image trial: `54569e1cf7f79fc30cb796005e07499759d902e4b506a940207aa666c5a5d394`.

Strict-verification trial: `f13178159a23e07d1f7a58f7f7339c6414ac868099324b88e244940cd8091e49`.

## Reproducing diagnostic comparisons

Diagnostics are off by default. Set `ANALYSIS_DIAGNOSTICS=1` in the API server's
environment **before starting it**. Its worker inherits the flag. The normal
API/result schema does not change. Each job writes a private `diagnostics.jsonl`
next to `job.json` under `backend/data/analysis/<job_id>/` with:

- actual sampled timestamps and sampling duration;
- proposal batches, candidate frame indexes, rule IDs and model observations;
- duplicate suppression and verification decisions, verification timestamps and duration;
- total worker duration (including unsuccessful attempts; inspect job status separately).

There are no images or credentials in the trace. Model observations still describe
the recording and must remain private. An optional trace-write error does not abort
analysis, so check trace completeness before drawing conclusions from an absent event.

From the repository root, preserve each run in its own ignored directory:

```powershell
& backend/.venv/Scripts/python.exe scripts/evaluate_dataset.py --archive C:/datasets/open.zip --run-name baseline-01
& backend/.venv/Scripts/python.exe scripts/evaluate_dataset.py --archive C:/datasets/open.zip --run-name candidate-01
```

Use separate consecutive runs with a fixed source version and the same local model;
do not run them concurrently against the single GPU worker. Replace the archive path
for your machine. Existing run names are rejected rather than overwritten. Named runs
write their report into `backend/data/validation/<run-name>/`, preserving the public
evaluation report. `--only`/`--limit` remain diagnostic subsets and do not write a
full evaluation report.

`manifest.json` records the model digest, Ollama/Python/OpenCV/platform versions,
archive SHA-256, Git HEAD and exact source hashes. The `source/` directory retains
the worker, rules, schemas, service, storage and evaluator used by that run, including
uncommitted changes. Inference parameters are captured in the worker source snapshot.
The API-reported model must match the manifest; a changed pipeline or model digest
invalidates completion. A manifest still marked `running` is not a completed run.

The local API and metadata reader must use the same server settings. These checks do
not measure independent generalization or eliminate normal inference variability.
Compare verdicts and per-video changes as well as aggregate scores. For localization,
use the same matched set and disclose missing events; never improve MAE by dropping
difficult predictions. The spreadsheet supplies no event types, so a nearby candidate
or a positive verifier decision does not establish the semantic cause of an error.

## Rejected full-data temporal-context experiment

The experiment added nine evenly spaced images to the evidence-verifier request for
`cash_not_secured` and `cashier_leaves_client`. It kept the 42-video proposal frames,
prompts, model, thresholds, and three returned evidence frames unchanged. Exact source,
Ollama version, model digest and archive SHA-256 are in the ignored
`backend/data/validation/dense-verification-01/manifest.json`.

| Measure | Fresh baseline | Nine-frame verifier |
| --- | ---: | ---: |
| Completed / failed | 42 / 0 | 42 / 0 |
| TP / TN / FP / FN | 17 / 6 / 14 / 5 | 17 / 4 / 16 / 5 |
| Verdict agreement | 54.76% | 50.00% |
| Precision / recall / F1 | 54.84% / 77.27% / 64.15% | 51.52% / 77.27% / 61.82% |
| Maximum processing time | 73.297 s | 98.360 s |
| Timestamp MAE on 17 predicted positives | 9.527 s | 8.422 s |
| Positive videos within diagnostic 2 s | 7 / 22 | 9 / 22 |

The candidate added two false-positive videos (X-10 and X-16), with no change in
TP or FN. A better timestamp MAE and two-second count do not compensate for worse
verdict accuracy and more false positives; labels contain no event types with which
to verify semantic localization. The agreed acceptance condition—fewer FP and FN no
higher than baseline—fails. Commit `88e72c7` is therefore reverted on the follow-up
branch. PR #5 merged that revert; `main` runs the restored baseline.
