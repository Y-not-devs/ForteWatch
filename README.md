# ForteWatch

Local-first video review service for identifying possible cashier-discipline violations. The Datathon 26 brief requires a reviewer to upload a recording and receive possible findings with timestamps, evidence frames, explanations, and references to the applicable rule. The system must run without cloud AI services.

## Project status

This repository is the application scaffold. The current UI can upload and list video files stored on the local server. Video analysis, evidence extraction, rule references, and the final results view are not implemented yet.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: React 19, TypeScript, Vite
- Local file storage for uploaded recordings
- Docker Compose for running the app

## Run locally

Requirements: Node.js 20.19+, Python 3.11+, and Git.

```bash
npm run setup
npm run dev
```

Open <http://localhost:5173>. The API is at <http://localhost:8000/api/docs>.

Uploads are saved under `backend/data/uploads/`; this folder and the source dataset are excluded from Git. Keep the videos and annotation spreadsheet from `open.zip` out of the repository unless the team explicitly approves sharing them.

## Next implementation steps

1. Validate video formats and sizes and create an analysis job for each upload.
2. Inspect the annotation spreadsheet and define the violation labels and expected output schema.
3. Build a fully local video inference pipeline and capture timestamped evidence frames.
4. Research and map findings to public regulatory sources, then show the source and explanation in the UI.
5. Evaluate against the provided labeled clips and report limitations and false positives.

The detector must not send recordings or derived frames to external AI APIs.
