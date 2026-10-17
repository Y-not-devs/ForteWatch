"""Check the exact staged diff against local secrets before every commit.

Does not print matches, diff content or secret values.
"""
import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
diff = subprocess.check_output(['git', 'diff', '--cached', '--binary'], cwd=root)
files = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=root).decode().splitlines()
for file in files:
    if Path(file).name.startswith('.env') and Path(file).name != '.env.example':
        raise SystemExit('Refusing commit: a private environment file is staged')
for file in (root / '.env', root / 'backend/.env'):
    if file.exists():
        for name, value in dotenv_values(file).items():
            if value and len(value) >= 16 and re.search(r'KEY|SECRET|TOKEN|PASSWORD', name):
                if value.encode() in diff:
                    raise SystemExit('Refusing commit: a local credential occurs in the staged diff')
if re.search(rb'(?:sk-(?:proj-)?[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{30,}|AIza[A-Za-z0-9_-]{30,})', diff):
    raise SystemExit('Refusing commit: a credential-like value occurs in the staged diff')
print('Staged diff inspected: no local credentials or known credential patterns found.')
