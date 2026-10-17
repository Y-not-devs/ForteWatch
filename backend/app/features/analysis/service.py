import json
import logging
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

logger = logging.getLogger(__name__)


class JobManager:
    """One bounded GPU worker per server process; run uvicorn with one worker."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = Path(settings.analysis_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        # Hold an OS lock for the server lifetime. A second process must never
        # mark another live worker's jobs as interrupted during startup recovery.
        self.storage_lock = (self.root / ".worker.lock").open("a+b")
        try:
            self.storage_lock.seek(0, os.SEEK_END)
            if not self.storage_lock.tell():
                self.storage_lock.write(b"0")
                self.storage_lock.flush()
            self.storage_lock.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.storage_lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.storage_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.storage_lock.close()
            raise RuntimeError(
                "Analysis storage is already owned by another server process"
            ) from None
        self.slot = threading.BoundedSemaphore(1)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")
        self.process: subprocess.Popen | None = None
        self.stopping = False
        self._fallback_jobs: dict[str, Job] = {}
        for path in self.root.glob("*/job.json"):
            job = Job.model_validate_json(path.read_text(encoding="utf-8"))
            if job.status == "processing":
                job.status, job.stage = "failed", "interrupted"
                job.error = "Server restarted during analysis. Please upload the video again."
                atomic_json(path, job.model_dump_json())

    def _release_slot(self) -> None:
        try:
            self.slot.release()
        except ValueError:
            pass

    def _save_terminal_job(
        self, directory: Path, job: Job, max_attempts: int = 5, delay: float = 0.05
    ) -> bool:
        target = directory / "job.json"
        content = job.model_dump_json()
        for attempt in range(max_attempts):
            try:
                atomic_json(target, content)
                self._fallback_jobs.pop(job.job_id, None)
                return True
            except OSError as exc:
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                else:
                    logger.error(
                        "Failed to persist terminal status for job %s after %d attempts: %s",
                        job.job_id,
                        max_attempts,
                        exc,
                    )
        self._fallback_jobs[job.job_id] = Job(
            job_id=job.job_id,
            status="failed",
            stage="failed",
            error="Analysis results could not be saved to storage",
            elapsed_sec=job.elapsed_sec,
        )
        return False

    async def submit(self, file: UploadFile) -> Job:
        if Path(file.filename or "").suffix.lower() != ".mov":
            raise HTTPException(415, "A .mov video is required")
        if self.stopping or not self.slot.acquire(blocking=False):
            raise HTTPException(
                429,
                "Analyzer is busy. Retry after the current job completes.",
                headers={"Retry-After": "10"},
            )
        slot_held = True
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
            slot_held = False
            return job
        except BaseException:
            try:
                (directory / "input.mov").unlink(missing_ok=True)
            except OSError as exc:
                logger.warning(
                    "Failed to remove temporary video on rejected upload for job %s: %s",
                    directory.name,
                    exc,
                )
            raise
        finally:
            if slot_held:
                self._release_slot()

    def get(self, job_id: str) -> Job:
        if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise HTTPException(404, "Job not found")
        path = self.root / job_id / "job.json"
        if not path.is_file():
            if job_id in self._fallback_jobs:
                return self._fallback_jobs[job_id]
            raise HTTPException(404, "Job not found")
        try:
            content = None
            for attempt in range(3):
                try:
                    content = path.read_text(encoding="utf-8")
                    break
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.02)
                    else:
                        raise
            if content is None:
                raise HTTPException(404, "Job not found")
            job = Job.model_validate_json(content)
        except OSError:
            if job_id in self._fallback_jobs:
                return self._fallback_jobs[job_id]
            raise
        if job.status == "processing" and job_id in self._fallback_jobs:
            return self._fallback_jobs[job_id]
        progress = path.with_name("progress.json")
        if job.status == "processing" and progress.is_file():
            try:
                state = json.loads(progress.read_text(encoding="utf-8"))
            except PermissionError:
                # Windows/OneDrive can briefly lock the optional progress snapshot.
                # Keep the durable processing state and try again on the next poll.
                pass
            else:
                job.progress, job.stage = state["progress"], state["stage"]
        return job

    def _run(self, directory: Path) -> None:
        started = time.monotonic()
        job = Job(job_id=directory.name)
        env = os.environ.copy()
        # No API credentials are needed by the video worker.
        env.pop("ANALYSIS_API_KEY", None)
        slot_held = True
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                self.process.wait(timeout=self.settings.analysis_timeout_seconds)
            except subprocess.TimeoutExpired:
                try:
                    self.process.kill()
                    self.process.wait()
                except OSError:
                    pass
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
            self.process = None
            try:
                try:
                    (directory / "input.mov").unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        "Failed to remove temporary video for job %s: %s",
                        directory.name,
                        exc,
                    )
                self._save_terminal_job(directory, job)
            finally:
                if slot_held:
                    slot_held = False
                    self._release_slot()

    def close(self):
        self.stopping = True
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.storage_lock.close()

