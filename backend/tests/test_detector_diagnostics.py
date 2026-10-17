import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.features.analysis import worker
from app.features.analysis.schemas import ModelEvent
from app.features.analysis.worker import diagnostic


def test_diagnostics_opt_in_and_private(tmp_path, monkeypatch):
    monkeypatch.delenv("ANALYSIS_DIAGNOSTICS", raising=False)
    diagnostic(tmp_path, "proposal", candidates=[])
    assert not list(tmp_path.iterdir())
    monkeypatch.setenv("ANALYSIS_DIAGNOSTICS", "1")
    diagnostic(tmp_path, "verification", confirmed=False, timecode_sec=12.5)
    diagnostic(tmp_path, "finished", elapsed_sec=20)
    rows = [json.loads(line) for line in
            (tmp_path / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {"event": "verification", "confirmed": False, "timecode_sec": 12.5},
        {"event": "finished", "elapsed_sec": 20},
    ]


def test_optional_diagnostic_write_failure_does_not_abort(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYSIS_DIAGNOSTICS", "1")

    def locked(*args, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "open", locked)
    diagnostic(tmp_path, "proposal", candidates=[])


@pytest.mark.parametrize("confirmed", [True, False])
def test_tracing_preserves_results_and_records_rejections(tmp_path, monkeypatch, confirmed):
    writer = cv2.VideoWriter(str(tmp_path / "input.mov"),
                             cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64))
    assert writer.isOpened()
    for _ in range(30):
        writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
    writer.release()
    event = ModelEvent(frame_index=1, rule_id="personal_items",
                       observation="A phone is handled on the staff side.")
    monkeypatch.setattr(worker, "check_local_model", lambda *_: None)
    monkeypatch.setattr(worker, "infer", lambda *_: [event])
    monkeypatch.setattr(worker, "verify_event", lambda *_: confirmed)
    monkeypatch.delenv("ANALYSIS_DIAGNOSTICS", raising=False)
    baseline = worker.analyze(tmp_path, "http://127.0.0.1:11434", "test", 20)
    monkeypatch.setenv("ANALYSIS_DIAGNOSTICS", "1")
    traced = worker.analyze(tmp_path, "http://127.0.0.1:11434", "test", 20)
    assert baseline == traced
    trace = [json.loads(line) for line in
             (tmp_path / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in trace] == [
        "sampling", "proposal", "verification", "finished",
    ]
    assert trace[1]["candidates"] == [event.model_dump()]
    assert trace[2]["confirmed"] is confirmed
    assert "image_base64" not in json.dumps(trace)
