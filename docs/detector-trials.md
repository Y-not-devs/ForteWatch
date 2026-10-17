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
