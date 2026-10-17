import os
from pathlib import Path


def atomic_json(path: Path, content: str) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)
