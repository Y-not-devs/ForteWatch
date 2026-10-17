"""Regression checks for real label formats and honest benchmark denominators."""

import importlib.util
import io
import json
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


@pytest.mark.parametrize("name", ["../escape", "nested/run", " ", "a" * 65])
def test_named_run_rejects_invalid_directory(name, monkeypatch):
    monkeypatch.setattr(evaluation.sys, "argv", [
        "evaluate_dataset.py", "--archive", "open.zip", "--run-name", name,
    ])
    with pytest.raises(SystemExit) as exc:
        evaluation.main()
    assert exc.value.code == 2


def test_named_run_does_not_overwrite_existing_results(tmp_path, monkeypatch):
    saved = tmp_path / "backend/data/validation/baseline"
    saved.mkdir(parents=True)
    metrics = saved / "metrics.json"
    metrics.write_text("preserve me", encoding="utf-8")
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setenv("ANALYSIS_API_KEY", "test-key")
    monkeypatch.setattr(evaluation.sys, "argv", [
        "evaluate_dataset.py", "--archive", "open.zip", "--run-name", "baseline",
    ])
    with pytest.raises(SystemExit) as exc:
        evaluation.main()
    assert exc.value.code == 2
    assert metrics.read_text(encoding="utf-8") == "preserve me"


def test_manifest_records_exact_source_model_and_dataset_without_credentials(tmp_path, monkeypatch):
    from app.core import config

    sources = tmp_path / "backend/app/features/analysis"
    sources.mkdir(parents=True)
    for name in ("worker.py", "schemas.py", "rules.py", "service.py", "storage.py"):
        (sources / name).write_bytes(b"source snapshot\n")
    archive = tmp_path / "open.zip"
    archive.write_bytes(b"private dataset")
    run = tmp_path / "run"
    run.mkdir()
    settings = SimpleNamespace(ollama_url="http://127.0.0.1:11434",
                               analysis_model="local:test", analysis_timeout_seconds=280)

    def get(url):
        data = ({"models": [{"name": "local:test", "digest": "model-digest"}]}
                if url.endswith("/tags") else {"version": "test-version"})
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))

    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    monkeypatch.setattr(evaluation.httpx, "Client",
                        lambda **kwargs: nullcontext(SimpleNamespace(get=get)))
    monkeypatch.setattr(evaluation.subprocess, "check_output", lambda *a, **k: "head\n")
    monkeypatch.setattr(evaluation.platform, "platform", lambda: "test-platform")
    monkeypatch.setenv("ANALYSIS_API_KEY", "secret-must-not-be-recorded")
    manifest = evaluation.capture_run_manifest(run, archive)
    assert manifest["model"]["digest"] == "model-digest"
    assert manifest["status"] == "running"
    assert manifest["archive_sha256"] == evaluation.hashlib.sha256(b"private dataset").hexdigest()
    assert (run / "source/worker.py").read_bytes() == b"source snapshot\n"
    assert "secret-must-not-be-recorded" not in json.dumps(manifest)
    assert not (run / "open.zip").exists()
