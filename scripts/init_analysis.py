"""Generate project-only local credentials without printing them."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = root / ".env"
text = (
    env.read_text(encoding="utf-8")
    if env.exists()
    else (root / ".env.example").read_text(encoding="utf-8")
)
for name in ("ANALYSIS_API_KEY", "SECRET_KEY"):
    lines = text.splitlines()
    existing = next((line for line in lines if line.startswith(name + "=")), None)
    if existing is None or not existing.split("=", 1)[1].strip():
        value = f"{name}={secrets.token_urlsafe(32)}"
        text = text.replace(existing, value) if existing else text + "\n" + value + "\n"
env.write_text(text, encoding="utf-8")
print("Local credentials configured in .env (values are not printed).")
