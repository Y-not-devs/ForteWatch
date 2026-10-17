"""Exercise the actual HTTP upload/poll/result contract on every archive video.

Never feeds labels, filenames or expected timestamps to the inference worker.
Evidence stays in private backend/data; public report contains metrics only.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

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
    parser.add_argument(
        "--only", nargs="+", help="Diagnostic subset; never publishes a full report"
    )
    args = parser.parse_args()
    key = os.environ.get("ANALYSIS_API_KEY") or dotenv_values(ROOT / ".env")["ANALYSIS_API_KEY"]
    private = ROOT / "backend/data/validation"
    private.mkdir(parents=True, exist_ok=True)
    output = ROOT / "docs/evaluation.md"
    output.parent.mkdir(exist_ok=True)
    rows = []
    with zipfile.ZipFile(args.archive) as archive:
        workbook = openpyxl.load_workbook(
            io.BytesIO(archive.read("open/open_labels.xlsx")),
            read_only=True,
            data_only=True,
        )
        labels = {
            normalized(str(name)): ("no_violation" if "без" in str(label).lower() else "violation")
            for name, _, label in list(workbook.active.values)[1:]
        }
        videos = [name for name in archive.namelist() if name.endswith(".mov")]
        assert len(videos) == len(labels) == 42
        assert {normalized(name) for name in videos} == set(labels)
        selected = (
            [name for name in videos if normalized(name) in args.only] if args.only else videos
        )
        for index, name in enumerate(selected[: args.limit]):
            started = time.monotonic()
            row = {
                "video": Path(name).name,
                "expected": labels[normalized(name)],
                "received": None,
                "seconds": 0,
                "error": "",
                "job_id": None,
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
                            row["received"] = result["verdict"]
                            break
                        time.sleep(0.5)
                    else:
                        raise TimeoutError("No terminal result within 300 seconds")
            except Exception as exc:
                row["error"] = str(exc).replace(str(key), "[REDACTED]")[:250]
            row["seconds"] = round(time.monotonic() - started, 3)
            if row["seconds"] >= 300:
                row["error"] = row["error"] or "Exceeded 300 seconds"
            rows.append(row)
            (private / "metrics.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(
                f"{index + 1}/{len(videos)} {ascii(row['video'])} "
                f"{row['received']} {row['seconds']:.1f}s {row['error']}",
                flush=True,
            )
    succeeded = sum(not row["error"] for row in rows)
    matched = sum(row["received"] == row["expected"] and not row["error"] for row in rows)
    script_hash = hashlib.sha256(
        (ROOT / "backend/app/features/analysis/worker.py").read_bytes()
    ).hexdigest()
    text = f"""# Real-video HTTP evaluation

Archive: `open.zip`; expected verdicts: `open/open_labels.xlsx`.
Run: {time.strftime("%Y-%m-%d %H:%M:%S %z")}. Local model: `qwen3.5:4b`.
Worker SHA-256: `{script_hash}`.
Completed: **{succeeded}/{len(rows)}**.
Verdict agreement: **{matched}/{len(rows)} ({matched / len(rows):.2%})**.
Maximum upload-to-result time: **{max(row["seconds"] for row in rows):.3f} seconds**.

This is agreement on the provided development dataset, not held-out accuracy. No training or
filename/label lookup is performed. Two archive pairs are exact byte duplicates (4/47 and 5/48);
all 42 entries are submitted independently under the neutral filename `recording.mov`.
Every completed response was schema-validated and every evidence JPEG decoded. Videos,
frames, API keys and per-job responses are excluded from this report and Git.

| Video | Expected verdict | Received verdict | Upload-to-result seconds | Error |
| --- | --- | --- | ---: | --- |
"""
    for row in rows:
        text += (
            f"| {row['video']} | {row['expected']} | {row['received'] or '—'} | "
            f"{row['seconds']:.3f} | {row['error'] or '—'} |\n"
        )
    if not args.limit and not args.only:
        output.write_text(text, encoding="utf-8")
    print(f"COMPLETED={succeeded}/{len(rows)} MATCHED={matched}/{len(rows)}", flush=True)
    return 0 if succeeded == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
