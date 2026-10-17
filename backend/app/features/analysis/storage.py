import os
import time
from pathlib import Path


def atomic_json(path: Path, content: str, attempts: int = 1, delay: float = 0.05) -> None:
    temporary = path.with_suffix(".tmp")
    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            with temporary.open("w", encoding="utf-8") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(path)
            return
        except OSError as exc:
            last_error = exc
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            if attempt < attempts - 1:
                time.sleep(delay)
    if last_error is not None:
        raise last_error

