"""Isolated, killable local inference process. No dataset/labels access or cloud fallback."""

import base64
import json
import math
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np
from pydantic import ValidationError

from app.features.analysis.rules import RULES
from app.features.analysis.schemas import (
    AnalysisResult,
    EvidenceCheck,
    EvidenceFrame,
    ModelResponse,
    Violation,
)
from app.features.analysis.storage import atomic_json

MAX_FRAMES = 48
BATCH_SIZE = 8
LIMITATIONS = (
    "Предварительная проверка человеком обязательна. Анализируются до 48 кадров, равномерно "
    "распределённых по ролику: краткие действия между кадрами могут быть пропущены. "
    "Поддерживаются только личные вещи в кассовой зоне, перемещение банкнот в одежду/личные "
    "вещи, оставление наличных без наблюдения или после ухода клиента, уход кассира при "
    "остающемся клиенте. Принадлежность предметов и полномочия людей "
    "не устанавливаются. Отсутствие найденных признаков не гарантирует отсутствие нарушений."
)
PROMPT = """Review a chronological contact sheet from bank cashier CCTV. Each tile has a local
frame_index F0, F1, etc and the time in seconds. Cashier is the person at the computer on the
staff side of the counter; visitors are on the opposite side. Observe actions, not identities.
Flag ONLY these review indicators, with clear visible evidence:
- personal_items: cashier visibly handles a mobile phone, eats/drinks, or stores a personal
  handbag/backpack on the staff working surface. Bank equipment, cash counting machines,
  documents, visitor belongings and merely touching a face are NOT personal_items.
- cash_concealment: clearly visible banknotes are moved by the cashier into clothing or a
  personal bag, away from the normal drawer. Ordinary cash transfers/counting are NOT suspicious.
- unattended_cash: clearly visible loose banknotes remain on the accessible counter while
  the cashier has physically left the desk. A seated cashier looking away is NOT this event.
- cash_not_secured: banknotes from a preceding customer visibly remain loose on the staff
  counter after that customer leaves, possibly while the next customer arrives. Require
  visible banknotes and the customer's departure; do not assume documents are banknotes.
- cashier_leaves_client: the staff cashier physically leaves the workstation while the
  customer remains waiting. An arriving/leaving customer is NOT the cashier leaving.
Return events=[] if none of these are clearly visible. Do not flag leaning, normal customer
arrival, normal handovers, computer work, or a drawer opening. Do not infer cash ownership,
authorization, computer records, missing paperwork, identity, guilt or any invisible action.
For each DISTINCT episode choose the clearest tile's frame_index and one rule_id.
Describe exactly the visible object, location and action, with cautious language. Do not
invent rules or timestamps. Multiple different indicators are allowed. Output only JSON.
"""


class AnalysisError(Exception):
    pass


def progress(directory: Path, value: int, stage: str):
    atomic_json(directory / "progress.json", json.dumps({"progress": value, "stage": stage}))


def jpeg(frame: np.ndarray, max_width: int = 960) -> str:
    if frame.shape[1] > max_width:
        frame = cv2.resize(frame, (max_width, round(frame.shape[0] * max_width / frame.shape[1])))
    ok, data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise AnalysisError("Could not encode evidence frame")
    return base64.b64encode(data).decode("ascii")


def read_frame(capture, timestamp: float, fps: float):
    index = round(timestamp * fps)
    # MOV variable-frame-rate indexes can seek just past the last decodable packet,
    # even when a sequential read succeeds. Try nearby earlier frames and report
    # the decoder's actual PTS, never the requested timestamp as fabricated evidence.
    for offset in range(3):
        target = max(0, index - offset)
        capture.set(cv2.CAP_PROP_POS_FRAMES, target)
        ok, frame = capture.read()
        if ok and frame is not None:
            actual = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            return actual if actual > 0 else target / fps, frame
    # Some VFR MOVs cannot seek to any of their last few packets. A sequential
    # decode reaches the real frame without relying on the container's seek index.
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame = None
    for _ in range(index + 1):
        ok, frame = capture.read()
        if not ok or frame is None:
            raise AnalysisError("Video contains an unreadable frame")
    actual = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
    return actual if actual > 0 else index / fps, frame


def contact_sheet(frames):
    columns, width = 3, 384
    rows = math.ceil(len(frames) / columns)
    # Portrait MOVs need taller tiles; forcing them into 320x180 reduced the
    # entire workstation to ~98 pixels wide and hid small visible objects.
    portrait = frames[0][1].shape[0] > frames[0][1].shape[1]
    image_height = 512 if portrait else 216
    tile_height = image_height + 20
    canvas = np.zeros((rows * tile_height, columns * width, 3), dtype=np.uint8)
    for index, (timestamp, frame) in enumerate(frames):
        x, y = index % columns * width, index // columns * tile_height
        scale = min(width / frame.shape[1], image_height / frame.shape[0])
        image = cv2.resize(frame, (round(frame.shape[1] * scale), round(frame.shape[0] * scale)))
        left = x + (width - image.shape[1]) // 2
        canvas[y + 20 : y + 20 + image.shape[0], left : left + image.shape[1]] = image
        cv2.putText(
            canvas,
            f"F{index}  {timestamp:.2f}s",
            (x + 4, y + 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
        )
    return jpeg(canvas, max_width=columns * width)


def verify_event(client, url, model, frames, rule_id, deadline):
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining < 3:
            raise AnalysisError("Local evidence verification exceeded its time limit")
        response = client.post(
            f"{url}/api/chat",
            timeout=remaining,
            json={
                "model": model,
                "stream": False,
                "think": False,
                "keep_alive": "30m",
                "format": EvidenceCheck.model_json_schema(),
                "options": {"num_ctx": 8192, "num_predict": 500, "temperature": 0, "seed": 7},
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Describe these bank CCTV frames independently in chronological order. "
                            + "Frame timestamps in seconds: "
                            + ", ".join(f"F{i}={t:.3f}" for i, (t, _) in enumerate(frames))
                            + ". Gaps may occur. Do not identify faces, infer authorization or "
                            "computer data. Return JSON describing the visible facts, not a "
                            "yes/no verdict. Mark each boolean true ONLY with clear evidence: "
                            "cashier_left_workstation requires a before/after sequence showing "
                            "the staff member leaving, not a visitor leaving or a reflection; "
                            "customer_still_at_counter means a visitor remains at the counter "
                            "after the staff member leaves; banknotes_on_counter requires loose "
                            "banknotes, not documents or equipment; previous_customer_departed "
                            "requires a visible customer departure while those banknotes remain; "
                            "cashier_personal_item requires staff handling a clearly visible "
                            "mobile phone, eating/drinking, or a personal bag on the staff desk; "
                            "banknotes_into_personal_storage requires visible banknotes moving "
                            "into clothing or a personal bag. False for absent or uncertain facts. "
                            "Identify the staff side by the computer and equipment, not clothing "
                            "or image position. Reflections are not additional people. "
                            "In observation describe ONLY what these frames show, including "
                            "absence of evidence when relevant. Do not repeat a suspected event."
                        ),
                        "images": [jpeg(frame, max_width=640) for _, frame in frames],
                    }
                ],
            },
        )
        response.raise_for_status()
        try:
            check = EvidenceCheck.model_validate_json(
                response.json()["message"]["content"]
            )
            return check if check.supports(rule_id) else None
        except (ValueError, KeyError):
            if attempt == 2:
                raise AnalysisError("Local evidence verifier returned invalid JSON") from None
    raise AssertionError("Unreachable")


def check_local_model(client, url: str, model: str):
    parsed = urlparse(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.path not in {"", "/"}
    ):
        raise AnalysisError("Only a loopback HTTP Ollama server is permitted")
    if "cloud" in model.lower() or "/" in model:
        raise AnalysisError("Only a locally installed model is permitted")
    tags = client.get(f"{url}/api/tags", timeout=5)
    tags.raise_for_status()
    if model not in {item["name"] for item in tags.json()["models"]}:
        raise AnalysisError("Local model is missing. Install the documented model before analysis.")
    response = client.post(f"{url}/api/show", json={"model": model}, timeout=10)
    response.raise_for_status()
    details = response.json()
    if details.get("remote_model") or details.get("remote_host"):
        raise AnalysisError("Remote model execution is forbidden")
    if "vision" not in details.get("capabilities", []):
        raise AnalysisError("Configured local model does not support images")


def infer(client, url, model, frames, deadline):
    image = contact_sheet(frames)
    schema = ModelResponse.model_json_schema()
    schema["$defs"]["ModelEvent"]["properties"]["frame_index"]["maximum"] = len(frames) - 1
    failure = "invalid_json"
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining < 3:
            raise AnalysisError("Local inference exceeded its processing time limit")
        response = client.post(
            f"{url}/api/chat",
            timeout=remaining,
            json={
                "model": model,
                "stream": False,
                "think": False,
                "keep_alive": "30m",
                "format": schema,
                "options": {"num_ctx": 8192, "num_predict": 1600, "temperature": 0, "seed": 7},
                "messages": [{"role": "user", "content": PROMPT, "images": [image]}],
            },
        )
        response.raise_for_status()
        try:
            result = ModelResponse.model_validate_json(response.json()["message"]["content"])
            if any(event.frame_index >= len(frames) for event in result.events):
                raise ValueError("Model referred to a non-existent frame")
            return result.events
        except (ValueError, KeyError) as exc:
            failure = (
                ",".join(sorted({e["type"] for e in exc.errors(include_input=False)}))
                if isinstance(exc, ValidationError)
                else "invalid_frame_reference"
            )
            if attempt == 2:
                raise AnalysisError(
                    "Local model returned an invalid structured result: " + failure
                ) from None
    raise AssertionError("Unreachable")


def analyze(directory: Path, url: str, model: str, timeout: int) -> AnalysisResult:
    deadline = time.monotonic() + timeout - 2
    cv2.setNumThreads(2)
    capture = cv2.VideoCapture(str(directory / "input.mov"))
    try:
        fps, count = capture.get(cv2.CAP_PROP_FPS), capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not capture.isOpened() or not math.isfinite(fps) or fps <= 0 or count < 1:
            raise AnalysisError("File is not a readable video")
        duration = count / fps
        if not math.isfinite(duration) or duration <= 0:
            raise AnalysisError("Video duration is invalid")
        progress(directory, 5, "reading_video")
        sample_count = min(MAX_FRAMES, max(2, math.ceil(duration) + 1))
        frames = [
            read_frame(capture, float(t), fps)
            for t in np.linspace(0, max(0, (count - 1) / fps), sample_count)
        ]
        violations = []
        with httpx.Client(trust_env=False, follow_redirects=False) as client:
            check_local_model(client, url, model)
            for start in range(0, len(frames), BATCH_SIZE):
                batch = frames[start : start + BATCH_SIZE]
                progress(directory, 10 + round(75 * start / len(frames)), "local_inference")
                for event in infer(client, url, model, batch, deadline):
                    timestamp = round(batch[event.frame_index][0], 3)
                    if any(
                        v.rule.id == event.rule_id and abs(v.timecode_sec - timestamp) < 6
                        for v in violations
                    ):
                        continue
                    rule = RULES[event.rule_id]
                    evidence = []
                    evidence_images = []
                    if event.rule_id in {"cash_not_secured", "cashier_leaves_client"}:
                        global_index = start + event.frame_index
                        times = {
                            frames[max(0, global_index - 4)][0],
                            timestamp,
                            frames[min(len(frames) - 1, global_index + 4)][0],
                        }
                    else:
                        times = {
                            max(0, timestamp - 0.5),
                            timestamp,
                            min((count - 1) / fps, timestamp + 0.5),
                        }
                    for t in sorted(times):
                        actual, frame = read_frame(capture, t, fps)
                        evidence_images.append((actual, frame))
                        evidence.append(
                            EvidenceFrame(timestamp_sec=round(actual, 3), image_base64=jpeg(frame))
                        )
                    verified = verify_event(
                        client, url, model, evidence_images, event.rule_id, deadline
                    )
                    if verified is None:
                        continue
                    violations.append(
                        Violation(
                            type=rule.title,
                            timecode_sec=timestamp,
                            description=verified.observation,
                            evidence_frames=evidence,
                            rule=rule,
                        )
                    )
        progress(directory, 95, "preparing_evidence")
        return AnalysisResult(
            verdict="violation" if violations else "no_violation",
            violations=sorted(violations, key=lambda v: v.timecode_sec),
            model=model,
            sampled_frames=len(frames),
            duration_sec=round(duration, 3),
            limitations=LIMITATIONS,
        )
    finally:
        capture.release()


if __name__ == "__main__":
    directory = Path(sys.argv[1])
    try:
        result = analyze(directory, sys.argv[2].rstrip("/"), sys.argv[3], int(sys.argv[4]))
        atomic_json(directory / "result.json", result.model_dump_json())
    except AnalysisError as exc:
        atomic_json(directory / "error.json", json.dumps({"error": str(exc)}))
        sys.exit(1)
    except httpx.TimeoutException:
        atomic_json(directory / "error.json", json.dumps({"error": "Local model timed out"}))
        sys.exit(1)
    except httpx.HTTPError:
        atomic_json(
            directory / "error.json", json.dumps({"error": "Local model server unavailable"})
        )
        sys.exit(1)
    except Exception:
        atomic_json(directory / "error.json", json.dumps({"error": "Local video analysis failed"}))
        sys.exit(1)
