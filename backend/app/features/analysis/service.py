import json
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import BACKEND_DIR, Settings
from app.features.analysis.schemas import AnalysisResult, Job
from app.features.analysis.storage import atomic_json


class JobManager:
    """One bounded GPU worker per server process; run uvicorn with one worker."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = Path(settings.analysis_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.slot = threading.BoundedSemaphore(1)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")
        self.process: subprocess.Popen | None = None
        self.stopping = False
        for path in self.root.glob("*/job.json"):
            job = Job.model_validate_json(path.read_text(encoding="utf-8"))
            if job.status == "processing":
                job.status, job.stage = "failed", "interrupted"
                job.error = "Server restarted during analysis. Please upload the video again."
                atomic_json(path, job.model_dump_json())

    async def submit(self, file: UploadFile) -> Job:
        if Path(file.filename or "").suffix.lower() != ".mov":
            raise HTTPException(415, "A .mov video is required")
        if self.stopping or not self.slot.acquire(blocking=False):
            raise HTTPException(
                429,
                "Analyzer is busy. Retry after the current job completes.",
                headers={"Retry-After": "10"},
            )
        directory = self.root / uuid.uuid4().hex
        try:
            directory.mkdir()
            size = 0
            with (directory / "input.mov").open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_upload_mb * 1024 * 1024:
                        raise HTTPException(413, "Video exceeds the configured upload limit")
                    output.write(chunk)
            if not size:
                raise HTTPException(422, "Video is empty")
            job = Job(job_id=directory.name)
            atomic_json(directory / "job.json", job.model_dump_json())
            self.pool.submit(self._run, directory)
            return job
        except BaseException:
            (directory / "input.mov").unlink(missing_ok=True)
            self.slot.release()
            raise

    def get(self, job_id: str) -> Job:
        if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise HTTPException(404, "Job not found")
        path = self.root / job_id / "job.json"
        if not path.is_file():
            raise HTTPException(404, "Job not found")
        job = Job.model_validate_json(path.read_text(encoding="utf-8"))
        progress = path.with_name("progress.json")
        if job.status == "processing" and progress.is_file():
            state = json.loads(progress.read_text(encoding="utf-8"))
            job.progress, job.stage = state["progress"], state["stage"]
        return job

    def _run(self, directory: Path) -> None:
        started = time.monotonic()
        job = Job(job_id=directory.name)
        env = os.environ.copy()
        # No API credentials are needed by the video worker.
        env.pop("ANALYSIS_API_KEY", None)
        try:
            command = [
                sys.executable,
                "-m",
                "app.features.analysis.worker",
                str(directory),
                self.settings.ollama_url,
                self.settings.analysis_model,
                str(self.settings.analysis_timeout_seconds),
            ]
            self.process = subprocess.Popen(
                command,
                cwd=BACKEND_DIR,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                self.process.wait(timeout=self.settings.analysis_timeout_seconds)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                raise TimeoutError from None
            result_path = directory / "result.json"
            if self.process.returncode == 0 and result_path.is_file():
                result = AnalysisResult.model_validate_json(result_path.read_text(encoding="utf-8"))
                job = Job(
                    job_id=directory.name,
                    status="done",
                    progress=100,
                    stage="complete",
                    **result.model_dump(),
                )
            else:
                error_path = directory / "error.json"
                job.status, job.stage = "failed", "failed"
                job.error = (
                    json.loads(error_path.read_text(encoding="utf-8"))["error"]
                    if error_path.is_file()
                    else "Local analyzer exited unexpectedly"
                )
        except TimeoutError:
            job.status, job.stage = "failed", "timeout"
            job.error = "Local analysis exceeded its processing time limit"
        except Exception:
            job.status, job.stage = "failed", "failed"
            job.error = "Local analysis could not be completed"
        finally:
            job.elapsed_sec = round(time.monotonic() - started, 3)
            atomic_json(directory / "job.json", job.model_dump_json())
            (directory / "input.mov").unlink(missing_ok=True)
            self.process = None
            self.slot.release()

    def close(self):
        self.stopping = True
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
        self.pool.shutdown(wait=True, cancel_futures=True)
