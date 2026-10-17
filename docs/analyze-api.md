# Local video analysis

ForteWatch accepts MOV recordings and runs Qwen3.5-4B locally through Ollama. The same
upload/job endpoints serve the UI and jury. Existing `/api/health`, `/api/meta`, auth,
`/api/uploads` and `/uploads/...` behavior is preserved. The original upload UI remains
available at `/uploads`; the home page now shows analysis.

## Run

Requires Python 3.11+, Node 20.19+, Git and a running local Ollama server. The measured
hardware is an RTX 3050 Laptop GPU (6 GB VRAM) and 16 GB RAM. Use one Uvicorn worker.
The five-minute processing target is validated on this machine, not arbitrary CPU-only hosts.

From the repository root:

```sh
npm run setup
python scripts/init_analysis.py
node scripts/py.mjs ../scripts/prepare_model.py
npm run dev
```

Start Ollama before the preparation command. Preparation downloads missing weights once;
the already-installed model is reused. No model download occurs when a video is uploaded.
After preparation the service processes videos without internet access. Open
`http://localhost:5173`, enter the project-only `ANALYSIS_API_KEY` from your local `.env`,
choose a MOV recording and click **Запустить анализ**. No account registration is needed.
The UI keeps the key only in memory. It must never be put in a `VITE_*` variable.

For a single-port production-style local run:

```sh
npm start
```

Open `http://localhost:8000`. This builds and serves the frontend from FastAPI. A publicly
reachable jury deployment additionally needs the team's host and HTTPS reverse proxy;
this PR does not provision hosting or a public URL. Keep Ollama's port private.

## API contract

Both endpoints require `X-API-Key`. An unset server key fails closed with 503; a missing
or incorrect client key returns 401. Credentials are generated independently of other projects.

`POST /api/v1/analyze`, multipart field `file`: case-insensitive `.mov`, up to the configured
`MAX_UPLOAD_MB` (default 512). Returns 202 with `job_id` and `status: processing` immediately
after storage. Empty files return 422, other extensions 415, oversize uploads 413.
Invalid video content becomes a terminal `failed` job with a readable error.

`GET /api/v1/jobs/{job_id}` returns `processing`, `done` or `failed`. Unknown IDs return 404.
Progress is based on completed inference batches, not an estimated countdown. A done job
contains `verdict: violation | no_violation`, `violations`, processing duration and limitations.
Each violation includes `type`, `timecode_sec`, `description`, 1–3 JPEG `evidence_frames`
(`timestamp_sec`, `image_base64`) and a `rule` with document, section, URL and rationale.
No-verdict responses for processing/failed jobs must not be treated as clean videos.

```sh
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: <your-local-key>" -F "file=@recording.mov"
curl http://localhost:8000/api/v1/jobs/<job_id> -H "X-API-Key: <your-local-key>"
```

Only one GPU job is accepted at a time. A concurrent upload returns 429 with `Retry-After`;
there is no unbounded queue consuming the five-minute budget. The processing deadline
defaults to 280 seconds, leaving headroom for upload and response. A timed-out worker is
killed. Job metadata/evidence are stored atomically under private `backend/data/analysis`,
outside the public uploads mount. Input videos are deleted after terminal processing. A
server restart preserves terminal results and marks interrupted jobs `failed`; upload again
to retry. An OS lock prevents two servers from corrupting the same job store.

## Analyzer and source mapping

The worker samples up to 48 frames uniformly across the **entire** clip, including its end.
Groups of up to 8 timestamped tiles are passed to the local vision model. Structured output
uses frame indexes, which the server maps back to actual decoder timestamps. Evidence JPEGs
come from the original decoded video, not from generated imagery. VFR MOV seek failures at
EOF fall back up to two frames or a sequential decode, reporting the actual timestamp. Malformed
model results are retried up to three times; failures are not converted into clean verdicts.
Each candidate is independently checked by the local model again on larger evidence frames
before publication, to reduce false alarms caused by small contact-sheet tiles. Temporal rules
use more widely spaced before/after frames to retain the customer/staff departure context.

The initial detector supports five visual review indicators:

| Indicator | Source | Scope |
| --- | --- | --- |
| Personal items in staff cash workspace | NBK resolution 231, chapter 2, paragraph 1, clause 12 | Visible phone, food/drink or personal bag; ownership and formal workspace boundaries need human review |
| Banknotes moved into clothing/personal belongings | Chapter 2, clause 3(7), clause 14 | A review indicator, not proof of theft |
| Loose cash left when cashier leaves | Chapter 2, clause 3(7) | General safekeeping requirement, not a fabricated specific unattended-desk prohibition |
| Cash remains on the desk after the customer leaves | Chapter 2, paragraph 2, clause 20 | Customer departure and loose banknotes must both be visible; completion of the bank transaction needs human confirmation |
| Cashier leaves while a client remains | Chapter 2, paragraph 2, clause 22 | The staff member, not merely a visitor, must leave the workstation |

Official act: <https://adilet.zan.kz/rus/docs/V1900019680>.
The clause wording was checked against the original official publication of resolution 231:
<https://kazpravda.kz/uploads/redactors/files/5e2ed7157da541580128021.pdf>.
The Adilet page serves the consolidated text; a human should check applicability and amendments.
The model cannot invent a legal reference: only IDs from this reviewed catalog are accepted.
Normative sources are bundled in code; inference never fetches external websites.

Qwen model/license: <https://huggingface.co/Qwen/Qwen3.5-4B> (Apache-2.0).
Runtime API: <https://docs.ollama.com/api/chat>. Remote URLs, cloud model names and models
declaring a remote backend are rejected. HTTP clients ignore proxy environment variables
and do not follow redirects. No face recognition, identity extraction or audio analysis is used.

## Verification

```sh
npm test
npm run lint
npm run build
cd frontend
npx playwright install chromium
npm run test:e2e
```

The browser tests expect the built app already running at port 8000; override with
`TEST_BASE_URL` if needed. They deterministically cover progress, both terminal statuses,
evidence/source rendering and invalid-key errors with mocked API responses. The actual
video pipeline is exercised separately over real HTTP, with no inference mock:

```sh
node scripts/py.mjs ../scripts/evaluate_dataset.py --archive /path/to/open.zip
```

The evaluator submits all 42 archive videos under the neutral filename `recording.mov`,
polls each for at most 300 seconds, validates response schemas, decodes **every** evidence
JPEG and compares against `open_labels.xlsx`. It writes private job metrics to
`backend/data/validation` and a key/frame-free table to `docs/evaluation.md`. A failure or
timeout makes the evaluator exit nonzero. Run without other active analysis clients.

One actual browser upload (no mocked responses):

```sh
node scripts/check_real_ui.mjs /path/to/recording.mov
```

This checks the real pipeline, rendered evidence JPEGs and regulatory links. It reads the
local key at the transport boundary to prevent browser snapshots from retaining credentials.

## Assumptions and limitations

- This is a local VLM baseline covering the five indicators above, not an exhaustive
  classifier for every possible regulation or every labeled event. False positives and
  missed violations are measured in the report; a completed HTTP job does not imply accuracy.
- Uniform sampling can miss brief actions. Small objects, occlusion, unusual camera angles
  and actions outside the supported catalog can produce errors. No bank-system or document
  contents, authorization, cash amount, criminal intent or cash ownership is inferred.
- Supplied labels have a verdict/timecode but no violation categories. They are used only
  by the evaluator, never loaded by the worker or used as a lookup table. The original
  filename is not passed to the worker. No training is performed.
- The development archive contains two exact duplicate pairs (4/47 and 5/48), verified by
  SHA-256; the requested 42-row evaluation includes both entries. Agreement is not a
  held-out or unseen-angle generalization estimate.
- A single API key protects analysis access for the team/jury. The UI asks for it because
  embedding it in public JavaScript would defeat API authentication.
- Development and production-style native runs are verified here. The original Docker
  scaffold does not provision a colocated Ollama runtime; configure that before container deployment.
- Runtime videos, evidence, model weights, `.env` and test artifacts are excluded from Git.
  Before **every** commit run `node scripts/py.mjs ../scripts/check_staged_secrets.py` and
  `git diff --cached --check`. The scanner checks the exact staged diff without printing keys.
