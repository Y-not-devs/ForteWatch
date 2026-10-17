"""One-time weight download; never run during video processing."""

import httpx

with httpx.Client(base_url="http://127.0.0.1:11434", trust_env=False, timeout=None) as client:
    response = client.post("/api/show", json={"model": "qwen3.5:4b"})
    if response.status_code == 404:
        with client.stream("POST", "/api/pull", json={"model": "qwen3.5:4b"}) as download:
            download.raise_for_status()
            for line in download.iter_lines():
                import json

                state = json.loads(line)
                if state.get("error"):
                    raise SystemExit("Model download failed. Check the local Ollama server.")
        response = client.post("/api/show", json={"model": "qwen3.5:4b"})
    response.raise_for_status()
    if "vision" not in response.json().get("capabilities", []):
        raise SystemExit("Installed model does not support image input")
print("Local qwen3.5:4b is installed. Inference can now run offline.")
