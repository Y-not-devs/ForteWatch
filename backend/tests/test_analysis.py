import base64
import json
import subprocess
import time
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest

from app.core.config import Settings, get_settings
from app.features.analysis import service, worker
from app.features.analysis.schemas import Job, ModelEvent
from app.features.analysis.storage import atomic_json

HEADERS = {"X-API-Key": "test-key-not-a-real-credential"}


def test_key_required_on_both_routes(client):
    for headers in ({}, {"X-API-Key": "wrong"}):
        assert (
            client.post(
                "/api/v1/analyze", headers=headers, files={"file": ("clip.mov", b"data")}
            ).status_code
            == 401
        )
        assert client.get("/api/v1/jobs/" + "a" * 32, headers=headers).status_code == 401


def test_unconfigured_key_fails_closed(client):
    settings = get_settings()
    original = settings.analysis_api_key
    settings.analysis_api_key = ""
    try:
        assert client.get("/api/v1/jobs/" + "a" * 32, headers=HEADERS).status_code == 503
    finally:
        settings.analysis_api_key = original


def test_upload_validation_and_unknown_job(client):
    assert (
        client.post(
            "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mp4", b"data")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"")}
        ).status_code
        == 422
    )
    get_settings().max_upload_mb = 0
    assert (
        client.post(
            "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"a")}
        ).status_code
        == 413
    )
    for job_id in ["invalid", "a" * 32]:
        assert client.get("/api/v1/jobs/" + job_id, headers=HEADERS).status_code == 404


def test_processing_and_backpressure(client, monkeypatch):
    manager = client.app.state.analysis
    monkeypatch.setattr(manager.pool, "submit", lambda *_: None)
    accepted = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.MOV", b"video")}
    )
    assert accepted.status_code == 202
    job_id = accepted.json()["job_id"]
    assert accepted.json()["status"] == "processing"
    polled = client.get("/api/v1/jobs/" + job_id, headers=HEADERS).json()
    assert polled["status"] == "processing"
    assert polled["verdict"] is None
    busy = client.post("/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"video")})
    assert busy.status_code == 429 and busy.headers["retry-after"] == "10"


def test_corrupt_video_becomes_failed_and_releases_worker(client):
    for _ in range(2):
        response = client.post(
            "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"not a video")}
        )
        assert response.status_code == 202
        for _ in range(200):
            job = client.get("/api/v1/jobs/" + response.json()["job_id"], headers=HEADERS).json()
            if job["status"] != "processing":
                break
            time.sleep(0.05)
        assert job["status"] == "failed" and job["error"]
        assert not list(client.app.state.analysis.root.glob("*/input.mov"))


def test_restart_preserves_terminal_results_and_fails_interrupted(tmp_path):
    directory = tmp_path / ("a" * 32)
    directory.mkdir()
    atomic_json(directory / "job.json", Job(job_id=directory.name).model_dump_json())
    manager = service.JobManager(Settings(analysis_dir=str(tmp_path)))
    try:
        assert manager.get(directory.name).status == "failed"
        assert manager.get(directory.name).stage == "interrupted"
    finally:
        manager.close()


def test_second_server_cannot_interrupt_active_jobs(client):
    manager = client.app.state.analysis
    directory = manager.root / ("d" * 32)
    directory.mkdir()
    atomic_json(directory / "job.json", Job(job_id=directory.name).model_dump_json())
    with pytest.raises(RuntimeError, match="already owned"):
        service.JobManager(manager.settings)
    assert manager.get(directory.name).status == "processing"


def test_subprocess_timeout_is_killed_and_reported(client, monkeypatch):
    manager = client.app.state.analysis

    class TimedOut:
        returncode = 1

        def __init__(self, *args, **kwargs):
            self.killed = False

        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("worker", timeout)

        def kill(self):
            self.killed = True

    monkeypatch.setattr(service.subprocess, "Popen", TimedOut)
    directory = manager.root / ("b" * 32)
    directory.mkdir()
    (directory / "input.mov").write_bytes(b"video")
    manager.slot.acquire()
    manager._run(directory)
    job = manager.get(directory.name)
    assert job.status == "failed" and job.stage == "timeout"
    assert manager.slot.acquire(blocking=False)
    manager.slot.release()


@pytest.mark.parametrize(
    "events",
    [
        [],
        [
            ModelEvent(
                frame_index=1,
                rule_id="personal_items",
                observation="A phone is held above the staff desk.",
            )
        ],
    ],
)
@pytest.mark.parametrize("confirmed", [True, False])
def test_real_decoder_evidence_and_done_api(client, tmp_path, monkeypatch, events, confirmed):
    directory = tmp_path / "local-worker"
    directory.mkdir()
    path = directory / "input.mov"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 180))
    assert writer.isOpened()
    for i in range(20):
        writer.write(np.full((180, 320, 3), i * 10, dtype=np.uint8))
    writer.release()
    monkeypatch.setattr(worker, "check_local_model", lambda *_: None)
    monkeypatch.setattr(worker, "infer", lambda *_: events)
    monkeypatch.setattr(worker, "verify_event", lambda *_: confirmed)
    result = worker.analyze(directory, "http://127.0.0.1:11434", "qwen3.5:4b", 10)
    assert result.verdict == ("violation" if events and confirmed else "no_violation")
    for violation in result.violations:
        assert len(violation.evidence_frames) == 3
        for frame in violation.evidence_frames:
            raw = base64.b64decode(frame.image_base64)
            assert cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) is not None
    manager = client.app.state.analysis
    job_id = "c" * 32
    saved = manager.root / job_id
    saved.mkdir()
    job = Job(job_id=job_id, status="done", progress=100, **result.model_dump())
    atomic_json(saved / "job.json", job.model_dump_json())
    response = client.get("/api/v1/jobs/" + job_id, headers=HEADERS)
    assert response.status_code == 200 and response.json()["verdict"] == result.verdict


@pytest.mark.parametrize(
    "url,model",
    [
        ("https://example.com", "qwen3.5:4b"),
        ("http://127.0.0.1:11434", "qwen:cloud"),
        ("http://127.0.0.1:11434", "missing"),
    ],
)
def test_cloud_and_missing_models_rejected(url, model):
    def transport(request):
        return httpx.Response(200, json={"models": []})

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(worker.AnalysisError):
            worker.check_local_model(client, url, model)


def test_remote_model_rejected():
    def transport(request):
        return httpx.Response(
            200,
            json=(
                {"models": [{"name": "qwen3.5:4b"}]}
                if request.url.path.endswith("/tags")
                else {"remote_model": "remote", "capabilities": ["vision"]}
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(worker.AnalysisError):
            worker.check_local_model(client, "http://127.0.0.1:11434", "qwen3.5:4b")


def test_legacy_upload_endpoint_remains_available(client):
    response = client.post("/api/uploads", files={"file": ("clip.mov", b"legacy video")})
    assert response.status_code == 201
    assert len(client.get("/api/uploads").json()) == 1


def test_malformed_model_output_is_retried_before_failure():
    attempts = []

    def transport(request):
        attempts.append(request)
        content = '{"events":' if len(attempts) < 3 else '{"events": []}'
        return httpx.Response(200, json={"message": {"content": content}})

    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        assert (
            worker.infer(
                client, "http://127.0.0.1:11434", "qwen3.5:4b", [(0, frame)], time.monotonic() + 10
            )
            == []
        )
    assert len(attempts) == 3


def test_invalid_frame_is_not_returned_as_a_clean_verdict():
    attempts = []

    def transport(request):
        attempts.append(request)
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": '{"events":[{"frame_index":99,"rule_id":"personal_items",'
                    '"observation":"A visible phone is on the cashier desk."}]}'
                }
            },
        )

    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(worker.AnalysisError, match="invalid_frame_reference"):
            worker.infer(
                client, "http://127.0.0.1:11434", "qwen3.5:4b", [(0, frame)], time.monotonic() + 10
            )
    assert len(attempts) == 3


def test_broken_mov_seek_index_uses_sequential_decode_and_real_pts():
    class Capture:
        sequential = False
        index = 0
        last = 0

        def set(self, prop, value):
            self.index = int(value)
            self.sequential = value == 0

        def read(self):
            if not self.sequential:
                return False, None
            self.last = self.index
            self.index += 1
            return True, np.zeros((10, 10, 3), dtype=np.uint8)

        def get(self, prop):
            return self.last * 100

    timestamp, frame = worker.read_frame(Capture(), 0.5, 10)
    assert timestamp == 0.5 and frame.shape == (10, 10, 3)


def test_evidence_verifier_rejects_unconfirmed_candidate():
    def transport(request):
        return httpx.Response(200, json={"message": {"content": '{"confirmed":false}'}})

    frames = [(0, np.zeros((180, 320, 3), dtype=np.uint8))] * 3
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        assert not worker.verify_event(
            client,
            "http://127.0.0.1:11434",
            "qwen3.5:4b",
            frames,
            "unattended_cash",
            time.monotonic() + 10,
        )


def test_invalid_verification_fails_after_three_attempts():
    attempts = []

    def transport(request):
        attempts.append(request)
        return httpx.Response(200, json={"message": {"content": '{"confirmed":'}})

    frames = [(0, np.zeros((180, 320, 3), dtype=np.uint8))] * 3
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(worker.AnalysisError, match="verifier returned invalid JSON"):
            worker.verify_event(
                client,
                "http://127.0.0.1:11434",
                "qwen3.5:4b",
                frames,
                "personal_items",
                time.monotonic() + 10,
            )
    assert len(attempts) == 3


def test_locked_progress_snapshot_does_not_fail_job_polling(client, monkeypatch):
    manager = client.app.state.analysis
    job_id = "d" * 32
    directory = manager.root / job_id
    directory.mkdir()
    atomic_json(directory / "job.json", Job(job_id=job_id).model_dump_json())
    atomic_json(directory / "progress.json", '{"progress":40,"stage":"local_inference"}')
    read_text = type(directory).read_text

    def read(path, *args, **kwargs):
        if path.name == "progress.json":
            raise PermissionError("Temporary Windows file lock")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(type(directory), "read_text", read)
    response = client.get("/api/v1/jobs/" + job_id, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    monkeypatch.setattr(type(directory), "read_text", read_text)
    response = client.get("/api/v1/jobs/" + job_id, headers=HEADERS)
    assert response.json()["progress"] == 40


def test_unlink_error_during_finalization_preserves_terminal_status_and_releases_slot(
    client, monkeypatch
):
    original_unlink = Path.unlink

    def mock_unlink(path, *args, **kwargs):
        if path.name == "input.mov":
            raise PermissionError("Simulated Windows file lock on input.mov")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", mock_unlink)
    response = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"not a video")}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(200):
        job = client.get("/api/v1/jobs/" + job_id, headers=HEADERS).json()
        if job["status"] != "processing":
            break
        time.sleep(0.05)
    assert job["status"] == "failed"
    # Worker slot must be released so next upload is accepted
    next_response = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"not a video")}
    )
    assert next_response.status_code == 202


def test_unlink_error_on_rejected_upload_preserves_http_status_and_releases_slot(
    client, monkeypatch
):
    manager = client.app.state.analysis
    original_unlink = Path.unlink

    def mock_unlink(path, *args, **kwargs):
        if path.name == "input.mov":
            raise PermissionError("Simulated file lock on empty video cleanup")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    # 1. Empty video upload rejected with 422
    response_empty = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"")}
    )
    assert response_empty.status_code == 422

    # Worker slot must be free; next valid upload must be accepted
    monkeypatch.setattr(manager.pool, "submit", lambda *_: None)
    next_response = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"valid video")}
    )
    assert next_response.status_code == 202
    manager._release_slot()

    # 2. Oversized upload rejected with 413
    get_settings().max_upload_mb = 0
    try:
        response_oversized = client.post(
            "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"large")}
        )
        assert response_oversized.status_code == 413
        assert manager.slot.acquire(blocking=False)
        manager._release_slot()
    finally:
        get_settings().max_upload_mb = 500


def test_temporary_write_error_recovered_by_retry(client, monkeypatch):
    manager = client.app.state.analysis
    attempts = 0
    real_atomic_json = service.atomic_json

    def flaky_atomic_json(path, content, *args, **kwargs):
        nonlocal attempts
        if path.name == "job.json" and "processing" not in content:
            attempts += 1
            if attempts < 3:
                raise PermissionError("Temporary Windows file lock on job.json")
        return real_atomic_json(path, content, *args, **kwargs)

    monkeypatch.setattr(service, "atomic_json", flaky_atomic_json)

    response = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"not a video")}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(200):
        job = client.get("/api/v1/jobs/" + job_id, headers=HEADERS).json()
        if job["status"] != "processing":
            break
        time.sleep(0.05)
    assert job["status"] == "failed"
    assert attempts >= 3
    assert manager.slot.acquire(blocking=False)
    manager._release_slot()


def test_persistent_write_error_does_not_leak_slot_or_report_done(client, monkeypatch):
    class MockSuccessProcess:
        returncode = 0

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    def mock_popen(command, *args, **kwargs):
        directory = Path(command[3])
        result_data = {
            "verdict": "no_violation",
            "violations": [],
            "model": "qwen3.5:4b",
            "sampled_frames": 10,
            "duration_sec": 5.0,
            "limitations": "none",
        }
        (directory / "result.json").write_text(json.dumps(result_data), encoding="utf-8")
        return MockSuccessProcess()

    monkeypatch.setattr(service.subprocess, "Popen", mock_popen)

    real_atomic_json = service.atomic_json

    def failing_terminal_write(path, content, *args, **kwargs):
        if path.name == "job.json" and "processing" not in content:
            raise PermissionError("Permanent lock on job.json")
        return real_atomic_json(path, content, *args, **kwargs)

    monkeypatch.setattr(service, "atomic_json", failing_terminal_write)

    response = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"video")}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    for _ in range(200):
        job = client.get("/api/v1/jobs/" + job_id, headers=HEADERS).json()
        if job["status"] != "processing":
            break
        time.sleep(0.05)

    # Server could not persist terminal state: API must NOT report done!
    assert job["status"] != "done"
    assert job["status"] == "failed"
    assert "storage" in job["error"].lower() or "save" in job["error"].lower()

    # Slot must be released and next upload must be accepted
    next_response = client.post(
        "/api/v1/analyze", headers=HEADERS, files={"file": ("clip.mov", b"video")}
    )
    assert next_response.status_code == 202


def test_atomic_json_retries_and_cleans_up_tmp(tmp_path, monkeypatch):
    target = tmp_path / "data.json"
    attempts = 0
    original_replace = Path.replace

    def flaky_replace(self, target_path):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("Locked")
        return original_replace(self, target_path)

    monkeypatch.setattr(Path, "replace", flaky_replace)
    atomic_json(target, '{"key": "value"}', attempts=3)
    assert target.read_text(encoding="utf-8") == '{"key": "value"}'
    assert not target.with_suffix(".tmp").exists()

    # With persistent failure, it cleans up .tmp and raises
    def permanent_fail(*args, **kwargs):
        raise PermissionError("Permanent")

    monkeypatch.setattr(Path, "replace", permanent_fail)
    with pytest.raises(PermissionError):
        atomic_json(target, '{"fail": true}', attempts=2)
    assert not target.with_suffix(".tmp").exists()

