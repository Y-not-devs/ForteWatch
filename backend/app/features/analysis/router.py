import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile

from app.core.config import get_settings
from app.features.analysis.schemas import Job


def require_api_key(x_api_key: Annotated[str | None, Header()] = None):
    expected = get_settings().analysis_api_key
    if not expected:
        raise HTTPException(503, "Analysis API key is not configured on this server")
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid or missing X-API-Key")


router = APIRouter(prefix="/v1", tags=["analysis"], dependencies=[Depends(require_api_key)])


@router.post("/analyze", response_model=Job, status_code=202)
async def analyze(file: UploadFile, request: Request):
    return await request.app.state.analysis.submit(file)


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str, request: Request):
    return request.app.state.analysis.get(job_id)
