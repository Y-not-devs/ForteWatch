"""Regression checks for real label formats and honest benchmark denominators."""

import importlib.util
import io
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

spec = importlib.util.spec_from_file_location(
    "evaluate_dataset", Path(__file__).resolve().parents[2] / "scripts/evaluate_dataset.py",
)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


@pytest.mark.parametrize("value,expected", [
    ("22 секунда", 22), ("1минута 8 секунда", 68), ("1 мин 8 сек", 68),
    ("01:08", 68), ("1:08.5", 68.5), ("8,5 секунда", 8.5), (0, 0), (None, None),
])
def test_timecode_formats(value, expected):
    assert evaluation.parse_timecode(value) == expected


@pytest.mark.parametrize("value", ["unknown", "-1", "nan", "1:99", "1минута 80 секунда"])
def test_bad_timecode_is_not_silently_ignored(value):
    with pytest.raises(ValueError):
        evaluation.parse_timecode(value)


def test_latin_and_cyrillic_names_match():
    assert evaluation.normalized("open/videos/Х-3.mov") == evaluation.normalized("x-3")


def test_failures_and_misses_do_not_disappear_from_metrics():
    def row(expected, received, error="", localization=None):
        return {"expected": expected, "received": received, "error": error,
                "localization_error_sec": localization}

    metrics = evaluation.summarize([
        row("violation", "violation", localization=1.5),
        row("violation", "no_violation"),
        row("violation", None, "timeout"),
        row("no_violation", "violation"),
        row("no_violation", "no_violation"),
    ])
    assert (metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]) == (1, 1, 1, 1)
    assert metrics["accuracy"] == 2 / 5
    assert metrics["recall"] == 1 / 3
    assert metrics["precision"] == 1 / 2
    assert metrics["failed"] == 1
    assert metrics["localized"] == 1
    assert metrics["localization_mae_sec"] == 1.5
    assert metrics["within_2_sec"] == 1


def test_no_predictions_does_not_claim_zero_localization_error():
    metrics = evaluation.summarize([
        {"expected": "violation", "received": "no_violation", "error": ""},
    ])
    assert metrics["precision"] is None
    assert metrics["localization_mae_sec"] is None
    assert metrics["recall"] == 0


def test_busy_analyzer_does_not_publish_a_cascade_of_failed_video_results(tmp_path, monkeypatch):
    worker = tmp_path / "backend/app/features/analysis/worker.py"
    worker.parent.mkdir(parents=True)
    worker.write_text("test worker", encoding="utf-8")
    videos = [f"open/videos/X-{i}.mov" for i in range(42)]
    archive = SimpleNamespace(namelist=lambda: videos, open=lambda _: io.BytesIO(b"video"))
    labels = {evaluation.normalized(n): {"verdict": "no_violation", "timecode_sec": None}
              for n in videos}
    response = httpx.Response(429, request=httpx.Request("POST", "http://localhost/analyze"))
    client = SimpleNamespace(post=lambda *args, **kwargs: response)
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "load_labels", lambda _: labels)
    monkeypatch.setattr(evaluation, "pipeline_hash", lambda: "fixed")
    monkeypatch.setattr(evaluation.zipfile, "ZipFile", lambda _: nullcontext(archive))
    monkeypatch.setattr(evaluation.httpx, "Client", lambda **kwargs: nullcontext(client))
    monkeypatch.setattr(evaluation.sys, "argv", ["evaluate_dataset.py", "--archive", "open.zip"])
    monkeypatch.setenv("ANALYSIS_API_KEY", "test-key-not-a-real-credential")
    with pytest.raises(RuntimeError, match="evaluation is incomplete"):
        evaluation.main()
    assert not (tmp_path / "docs/evaluation.md").exists()
    assert not (tmp_path / "backend/data/validation/metrics.json").exists()
