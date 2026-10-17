# ForteWatch

Local-first video review service for identifying possible cashier-discipline violations. The Datathon 26 brief requires a reviewer to upload a recording and receive possible findings with timestamps, evidence frames, explanations, and references to the applicable rule. The system must run without cloud AI services.

## Project status

The app provides authenticated asynchronous MOV analysis through `/api/v1/analyze` and
`/api/v1/jobs/{job_id}`. The home page shows progress, a verdict, timestamped JPEG evidence,
explanations and reviewed rule references. Inference uses a fully local Qwen3.5-4B model.
The initial detector covers five visual review indicators; see the measured quality and
limitations rather than treating a clean result as a guarantee.

See [setup, API and assumptions](docs/analyze-api.md) and the
[real-video evaluation](docs/evaluation.md).

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: React 19, TypeScript, Vite
- Local file storage for uploaded recordings
- Docker Compose for running the app

## Run locally

Requirements: Node.js 20.19+, Python 3.11+, and Git.

```bash
npm run setup
python scripts/init_analysis.py
node scripts/py.mjs ../scripts/prepare_model.py
npm run dev
```

Open <http://localhost:5173>. The API is at <http://localhost:8000/api/docs>.

Uploads are saved under `backend/data/uploads/`; this folder and the source dataset are excluded from Git. Keep the videos and annotation spreadsheet from `open.zip` out of the repository unless the team explicitly approves sharing them.

Start local Ollama first. Model preparation downloads missing weights once, before processing.
Enter the generated `ANALYSIS_API_KEY` from local `.env` in the UI. Existing upload/list
functionality remains available at `/uploads`. Run `npm test`, `npm run lint` and `npm run build`
for the automated checks; the analysis guide describes browser and all-video validation.

The detector must not send recordings or derived frames to external AI APIs.
