"""Exercise the actual HTTP upload/poll/result contract on every archive video.

Never feeds labels, filenames or expected timestamps to the inference worker.
Evidence stays in private backend/data; public report contains metrics only.
"""

import argparse
import base64
import hashlib
import io
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np
import openpyxl
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.features.analysis.schemas import Job  # noqa: E402


def normalized(name):
    return Path(name).stem.upper().replace("\u0425", "X")


def parse_timecode(value):
    """Read the supplied single-event timestamps; reject malformed labels."""
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().lower().replace(",", ".")
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        seconds = float(text)
    elif match := re.fullmatch(r"(\d+):([0-5]\d(?:\.\d+)?)", text):
        seconds = 60 * int(match[1]) + float(match[2])
    elif match := re.fullmatch(
        r"(?:(\d+)\s*мин(?:ута|уты|ут)?\s*)?"
        r"(?:(\d+(?:\.\d+)?)\s*сек(?:унда|унды|унд)?\s*)?", text
    ):
        if not any(match.groups()):
            raise ValueError(f"Invalid label timestamp: {value!r}")
        if match[1] and match[2] and float(match[2]) >= 60:
            raise ValueError(f"Invalid label timestamp: {value!r}")
        seconds = 60 * int(match[1] or 0) + float(match[2] or 0)
    else:
        raise ValueError(f"Invalid label timestamp: {value!r}")
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"Invalid label timestamp: {value!r}")
    return seconds


def load_labels(archive):
    workbook = openpyxl.load_workbook(
        io.BytesIO(archive.read("open/open_labels.xlsx")), read_only=True, data_only=True,
    )
    try:
        labels = {}
        for name, timestamp, label in list(workbook.active.values)[1:]:
            key = normalized(str(name))
            verdict = {
                "нарушение": "violation", "без нарушения": "no_violation",
            }.get(str(label).strip().lower())
            if key in labels or verdict is None or name is None:
                raise ValueError(f"Duplicate or invalid label: {name!r}")
            seconds = parse_timecode(timestamp)
            if (verdict == "violation") != (seconds is not None):
                raise ValueError(f"Timestamp does not match verdict: {name!r}")
            labels[key] = {"verdict": verdict, "timecode_sec": seconds}
        return labels
    finally:
        workbook.close()


def summarize(rows):
    completed = [row for row in rows if not row["error"]]
    tp = sum(r["expected"] == r["received"] == "violation" for r in completed)
    tn = sum(r["expected"] == r["received"] == "no_violation" for r in completed)
    fp = sum(r["expected"] == "no_violation" and r["received"] == "violation"
             for r in completed)
    fn = sum(r["expected"] == "violation" and r["received"] == "no_violation"
             for r in completed)
    positives = sum(r["expected"] == "violation" for r in rows)
    errors = [r["localization_error_sec"] for r in completed
              if r.get("localization_error_sec") is not None]
    return {
        "completed": len(completed), "total": len(rows), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "failed": len(rows) - len(completed), "positives": positives,
        "accuracy": (tp + tn) / len(rows) if rows else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / positives if positives else None,
        "f1": 2 * tp / (2 * tp + fp + positives - tp) if tp + fp + positives else None,
        "localized": len(errors),
        "localization_mae_sec": statistics.mean(errors) if errors else None,
        "within_2_sec": sum(error <= 2 for error in errors),
    }


def percentage(value):
    return f"{value:.2%}" if value is not None else "N/A"


def pipeline_hash():
    digest = hashlib.sha256()
    for name in ("worker.py", "schemas.py", "rules.py", "service.py", "storage.py"):
        digest.update(name.encode())
        digest.update((ROOT / "backend/app/features/analysis" / name).read_bytes())
    return digest.hexdigest()


def capture_run_manifest(destination, archive):
    """Keep exact source and local model identity beside a named private run."""
    from app.core.config import get_settings

    settings = get_settings()
    if urlparse(settings.ollama_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Run metadata requires a local Ollama server")
    with httpx.Client(trust_env=False, follow_redirects=False, timeout=10) as client:
        response = client.get(settings.ollama_url.rstrip("/") + "/api/tags")
        response.raise_for_status()
        model = next(m for m in response.json()["models"]
                     if m["name"] == settings.analysis_model)
        response = client.get(settings.ollama_url.rstrip("/") + "/api/version")
        response.raise_for_status()
        version = response.json()["version"]
    sources = destination / "source"
    sources.mkdir()
    hashes = {}
    for name in ("worker.py", "schemas.py", "rules.py", "service.py", "storage.py"):
        content = (ROOT / "backend/app/features/analysis" / name).read_bytes()
        (sources / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    content = Path(__file__).read_bytes()
    (sources / "evaluate_dataset.py").write_bytes(content)
    hashes["evaluate_dataset.py"] = hashlib.sha256(content).hexdigest()
    with archive.open("rb") as source:
        archive_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    manifest = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip(),
        "source_sha256": hashes, "model": model, "ollama_version": version,
        "python": platform.python_version(), "opencv": cv2.__version__,
        "platform": platform.platform(), "archive_sha256": archive_sha256,
        "analysis_timeout_seconds": settings.analysis_timeout_seconds,
        "status": "running",
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return manifest


def validate_result(job):
    parsed = Job.model_validate(job)
    assert parsed.status == "done", parsed.error
    assert parsed.verdict in {"violation", "no_violation"}
    assert bool(parsed.violations) == (parsed.verdict == "violation")
    assert parsed.sampled_frames and parsed.duration_sec
    for violation in parsed.violations:
        assert 0 <= violation.timecode_sec < parsed.duration_sec
        assert violation.rule.section and violation.rule.url.startswith("https://adilet.zan.kz/")
        for frame in violation.evidence_frames:
            data = base64.b64decode(frame.image_base64, validate=True)
            assert data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")
            assert cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR) is not None
            assert 0 <= frame.timestamp_sec < parsed.duration_sec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--run-name", help="Unique private run directory; preserve earlier reports")
    parser.add_argument(
        "--only", nargs="+", help="Diagnostic subset; never publishes a full report"
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    if args.run_name and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", args.run_name):
        parser.error("--run-name must be 1–64 letters, digits, hyphens or underscores")
    key = os.environ.get("ANALYSIS_API_KEY") or dotenv_values(ROOT / ".env")["ANALYSIS_API_KEY"]
    private = ROOT / "backend/data/validation"
    private.mkdir(parents=True, exist_ok=True)
    output = ROOT / "docs/evaluation.md"
    manifest = None
    if args.run_name:
        private = private / args.run_name
        if private.exists():
            parser.error("Run directory already exists; choose a new --run-name")
        private.mkdir()
        output = private / "evaluation.md"
        manifest = capture_run_manifest(private, args.archive)
    output.parent.mkdir(exist_ok=True)
    rows = []
    with zipfile.ZipFile(args.archive) as archive:
        labels = load_labels(archive)
        videos = [name for name in archive.namelist() if name.endswith(".mov")]
        assert len(videos) == len(labels) == 42
        assert {normalized(name) for name in videos} == set(labels)
        selected = (
            [name for name in videos if normalized(name) in {normalized(n) for n in args.only}]
            if args.only else videos
        )
        if not selected:
            parser.error("No videos matched --only")
        script_hash = hashlib.sha256(
            (ROOT / "backend/app/features/analysis/worker.py").read_bytes()
        ).hexdigest()
        pipeline_sha = pipeline_hash()
        for index, name in enumerate(selected[: args.limit]):
            if pipeline_hash() != pipeline_sha:
                raise RuntimeError("Analyzer changed during evaluation; rerun with a fixed version")
            started = time.monotonic()
            row = {
                "video": Path(name).name,
                "expected": labels[normalized(name)]["verdict"],
                "expected_timecode_sec": labels[normalized(name)]["timecode_sec"],
                "predicted_timecodes_sec": [],
                "localization_error_sec": None,
                "worker_sha256": script_hash,
                "pipeline_sha256": pipeline_sha,
                "received": None,
                "seconds": 0,
                "error": "",
                "job_id": None,
                "model": None,
            }
            try:
                with httpx.Client(
                    base_url=args.url,
                    headers={"X-API-Key": key},
                    timeout=60,
                    trust_env=False,
                ) as client:
                    with archive.open(name) as video:
                        response = client.post(
                            "/api/v1/analyze",
                            files={"file": ("recording.mov", video, "video/quicktime")},
                        )
                    response.raise_for_status()
                    row["job_id"] = response.json()["job_id"]
                    while time.monotonic() - started < 300:
                        response = client.get("/api/v1/jobs/" + row["job_id"])
                        response.raise_for_status()
                        result = response.json()
                        if result["status"] != "processing":
                            validate_result(result)
                            if manifest and result["model"] != manifest["model"]["name"]:
                                raise ValueError("API model differs from recorded local model")
                            row["received"] = result["verdict"]
                            row["model"] = result["model"]
                            row["predicted_timecodes_sec"] = [
                                event["timecode_sec"] for event in result["violations"]
                            ]
                            if row["expected_timecode_sec"] is not None and result["violations"]:
                                row["localization_error_sec"] = min(
                                    abs(t - row["expected_timecode_sec"])
                                    for t in row["predicted_timecodes_sec"]
                                )
                            break
                        time.sleep(0.5)
                    else:
                        raise TimeoutError("No terminal result within 300 seconds")
            except Exception as exc:
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                    raise RuntimeError(
                        "Analyzer is busy; evaluation is incomplete. "
                        "No full report was written. Wait for the active job before rerunning."
                    ) from None
                row["error"] = str(exc).replace(str(key), "[REDACTED]")[:250]
            row["seconds"] = round(time.monotonic() - started, 3)
            if row["seconds"] >= 300:
                row["error"] = row["error"] or "Exceeded 300 seconds"
            rows.append(row)
            metrics_file = "subset_metrics.json" if args.only or args.limit else "metrics.json"
            (private / metrics_file).write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(
                f"{index + 1}/{len(selected[: args.limit])} {ascii(row['video'])} "
                f"{row['received']} {row['seconds']:.1f}s {row['error']}",
                flush=True,
            )
    if pipeline_hash() != pipeline_sha:
        raise RuntimeError("Analyzer changed during evaluation; rerun with a fixed version")
    if manifest:
        from app.core.config import get_settings

        with httpx.Client(trust_env=False, follow_redirects=False, timeout=10) as client:
            response = client.get(get_settings().ollama_url.rstrip("/") + "/api/tags")
            response.raise_for_status()
            digest = next(m["digest"] for m in response.json()["models"]
                          if m["name"] == manifest["model"]["name"])
        if digest != manifest["model"]["digest"]:
            raise RuntimeError("Model changed during evaluation; run is incomplete")
        manifest["status"] = "complete" if all(not row["error"] for row in rows) else "failed"
        manifest["total"] = len(rows)
        manifest["subset"] = bool(args.only or args.limit)
        (private / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
        )
    metrics = summarize(rows)
    succeeded = metrics["completed"]
    matched = metrics["tp"] + metrics["tn"]
    mae = metrics["localization_mae_sec"]
    mae_text = f"{mae:.3f} seconds" if mae is not None else "N/A"
    model_names = ", ".join(sorted({r["model"] for r in rows if r["model"]})) or "unavailable"
    text = f"""# Real-video HTTP evaluation

Archive: `open.zip`; expected verdicts: `open/open_labels.xlsx`.
Run: {time.strftime("%Y-%m-%d %H:%M:%S %z")}. Reported model: `{model_names}`.
Worker SHA-256: `{script_hash}`.
Pipeline SHA-256 (worker, schemas, rules, service, storage): `{pipeline_sha}`.
Completed: **{succeeded}/{len(rows)}**.
Verdict agreement: **{matched}/{len(rows)} ({matched / len(rows):.2%})**.
Maximum upload-to-result time: **{max(row["seconds"] for row in rows):.3f} seconds**.

Positive labels: **{metrics["positives"]}/{len(rows)}**.
TP: **{metrics["tp"]}**; TN: **{metrics["tn"]}**;
FP: **{metrics["fp"]}**; FN: **{metrics["fn"]}**; failed: **{metrics["failed"]}**.
Precision: **{percentage(metrics["precision"])}**;
end-to-end recall: **{percentage(metrics["recall"])}**; F1: **{percentage(metrics["f1"])}**.
Nearest-prediction timestamp MAE: **{mae_text}**, over **{metrics["localized"]}**
positive videos with a prediction.
Within 2 seconds: **{metrics["within_2_sec"]}/{metrics["positives"]}**
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
"""
    for row in rows:
        error = row["localization_error_sec"] if not row["error"] else None
        localization = f"{error:.3f}" if error is not None else "—"
        text += (
            f"| {row['video']} | {row['expected']} | {row['received'] or '—'} | "
            f"{row['seconds']:.3f} | {localization} | {row['error'] or '—'} |\n"
        )
    if not args.limit and not args.only:
        output.write_text(text, encoding="utf-8")
    print(f"COMPLETED={succeeded}/{len(rows)} MATCHED={matched}/{len(rows)}", flush=True)
    return 0 if succeeded == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
